import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

// POST: 키워드 수집 실행
export async function POST(request: Request) {
  // Vercel 환경에서는 수집 기능 비활성화
  if (process.env.VERCEL) {
    return NextResponse.json(
      {
        error: "수집 기능은 로컬 환경에서만 사용 가능합니다.",
        message: "GitHub Actions를 통해 자동 수집되거나, 로컬에서 직접 실행해주세요."
      },
      { status: 400 }
    );
  }

  try {
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
