import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

interface KeywordItem {
  query: string;
  country: string;
  limit: number;
  enabled: boolean;
}

interface KeywordsData {
  keywords: KeywordItem[];
  schedule: { time: string };
}

// 데이터 경로 (Vercel vs 로컬 자동 감지)
function getDataDir(): string {
  const vercelDataDir = path.join(process.cwd(), "data");
  const localDataDir = path.join(process.cwd(), "..", "data");

  if (fs.existsSync(vercelDataDir) && fs.existsSync(path.join(vercelDataDir, "raw"))) {
    return vercelDataDir;
  }
  return localDataDir;
}

// keywords.json에서 등록된 키워드 목록 읽기
function getRegisteredKeywords(): KeywordItem[] {
  const keywordsFile = path.join(getDataDir(), "keywords.json");
  try {
    if (fs.existsSync(keywordsFile)) {
      const content = fs.readFileSync(keywordsFile, "utf-8");
      const data: KeywordsData = JSON.parse(content);
      return data.keywords.filter(kw => kw.enabled);
    }
  } catch (e) {
    console.error("Error reading keywords.json:", e);
  }
  return [];
}

// GitHub Actions 워크플로우 트리거
async function triggerGitHubActions(): Promise<{ success: boolean; message: string }> {
  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER || "gptersvolka";
  const repo = process.env.GITHUB_REPO || "meta-library_v1";

  if (!token) {
    return {
      success: false,
      message: "GITHUB_TOKEN이 설정되지 않았습니다. 환경 변수를 확인해주세요.",
    };
  }

  try {
    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/collect-ads.yml/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github.v3+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ref: "main",
        }),
      }
    );

    if (response.status === 204) {
      return {
        success: true,
        message: "수집 작업이 GitHub Actions에서 시작되었습니다. 완료까지 약 10-30분 소요됩니다.",
      };
    } else {
      const errorText = await response.text();
      console.error("GitHub API error:", response.status, errorText);
      return {
        success: false,
        message: `GitHub Actions 트리거 실패: ${response.status}`,
      };
    }
  } catch (error) {
    console.error("GitHub API request failed:", error);
    return {
      success: false,
      message: "GitHub API 요청 실패",
    };
  }
}

// POST: 모든 등록된 키워드에 대해 수집 실행
export async function POST() {
  // Vercel 환경에서는 GitHub Actions 트리거
  if (process.env.VERCEL) {
    const result = await triggerGitHubActions();

    if (result.success) {
      return NextResponse.json({
        success: true,
        message: result.message,
        mode: "github_actions",
      });
    } else {
      return NextResponse.json(
        { error: result.message },
        { status: 400 }
      );
    }
  }

  // 로컬 환경에서는 직접 실행
  try {
    const keywords = getRegisteredKeywords();

    if (keywords.length === 0) {
      return NextResponse.json(
        { error: "등록된 키워드가 없습니다." },
        { status: 400 }
      );
    }

    const projectRoot = path.join(process.cwd(), "..");
    const results: { keyword: string; success: boolean; message: string }[] = [];

    // 순차적으로 각 키워드 수집
    for (const kw of keywords) {
      console.log(`[collect-all] Starting: ${kw.query}`);

      const exitCode = await new Promise<number>((resolve) => {
        const pythonProcess = spawn(
          "python",
          [
            "-m",
            "src.07_run_weekly",
            "--query",
            kw.query,
            "--country",
            kw.country || "KR",
            "--limit",
            String(kw.limit || 50),
            "--headless",
          ],
          {
            cwd: projectRoot,
            shell: true,
          }
        );

        pythonProcess.stdout.on("data", (data) => {
          console.log(`[collect-all] ${data}`);
        });

        pythonProcess.stderr.on("data", (data) => {
          console.error(`[collect-all error] ${data}`);
        });

        pythonProcess.on("close", (code) => {
          resolve(code ?? 1);
        });
      });

      results.push({
        keyword: kw.query,
        success: exitCode === 0,
        message: exitCode === 0 ? "수집 완료" : "수집 실패",
      });
    }

    const successCount = results.filter(r => r.success).length;
    const failCount = results.filter(r => !r.success).length;

    return NextResponse.json({
      success: true,
      message: `${successCount}개 키워드 수집 완료${failCount > 0 ? `, ${failCount}개 실패` : ""}`,
      results,
      mode: "local",
    });
  } catch (error) {
    console.error("Error running collection for all keywords:", error);
    return NextResponse.json(
      { error: "수집 실행 중 오류 발생" },
      { status: 500 }
    );
  }
}
