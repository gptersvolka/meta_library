import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

// GitHub Actions 워크플로우 트리거 (특정 키워드)
async function triggerGitHubActions(keyword: string): Promise<{ success: boolean; message: string }> {
  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER || "gptersvolka";
  const repo = process.env.GITHUB_REPO || "meta_library";

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
          inputs: {
            query: keyword,
          },
        }),
      }
    );

    if (response.status === 204) {
      return {
        success: true,
        message: `"${keyword}" 수집이 GitHub Actions에서 시작되었습니다. 완료까지 약 5-10분 소요됩니다.`,
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

// POST: 키워드 수집 실행
export async function POST(request: Request) {
  const body = await request.json();
  const { keyword, country = "KR", limit = 50 } = body;

  if (!keyword || typeof keyword !== "string") {
    return NextResponse.json(
      { error: "Invalid keyword" },
      { status: 400 }
    );
  }

  const trimmedKeyword = keyword.trim();
  if (!trimmedKeyword) {
    return NextResponse.json(
      { error: "Keyword cannot be empty" },
      { status: 400 }
    );
  }

  // Vercel 환경에서는 GitHub Actions 트리거
  if (process.env.VERCEL) {
    const result = await triggerGitHubActions(trimmedKeyword);

    if (result.success) {
      return NextResponse.json({
        success: true,
        keyword: trimmedKeyword,
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

  // 로컬 환경에서는 직접 Python 스크립트 실행
  try {
    // 프로젝트 루트 경로
    const projectRoot = path.join(process.cwd(), "..");

    // Python 스크립트 실행
    const pythonProcess = spawn(
      "python",
      [
        "-m",
        "src.07_run_weekly",
        "--query",
        trimmedKeyword,
        "--country",
        country,
        "--limit",
        String(limit),
        "--headless",
      ],
      {
        cwd: projectRoot,
        shell: true,
      }
    );

    let stdout = "";
    let stderr = "";

    pythonProcess.stdout.on("data", (data) => {
      stdout += data.toString();
      console.log(`[collect] ${data}`);
    });

    pythonProcess.stderr.on("data", (data) => {
      stderr += data.toString();
      console.error(`[collect error] ${data}`);
    });

    // 프로세스 완료 대기
    const exitCode = await new Promise<number>((resolve) => {
      pythonProcess.on("close", (code) => {
        resolve(code ?? 1);
      });
    });

    if (exitCode !== 0) {
      return NextResponse.json(
        {
          error: "Collection failed",
          details: stderr || stdout,
          exitCode,
        },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      keyword: trimmedKeyword,
      message: `키워드 "${trimmedKeyword}" 수집 완료`,
    });
  } catch (error) {
    console.error("Error running collection:", error);
    return NextResponse.json(
      { error: "Failed to run collection" },
      { status: 500 }
    );
  }
}
