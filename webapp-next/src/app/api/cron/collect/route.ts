import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

// Vercel Cron 또는 외부 호출용 스케줄 수집 API
// GET: 등록된 모든 키워드 자동 수집 실행

export const maxDuration = 300; // 5분 타임아웃 (Vercel Pro 필요)
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  // Vercel Cron 인증 (CRON_SECRET 환경변수 설정 시)
  const authHeader = request.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;

  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  try {
    console.log("[cron] 스케줄 수집 시작:", new Date().toISOString());

    // 프로젝트 루트 경로
    const projectRoot = path.join(process.cwd(), "..");

    // Python 스케줄러 run_now 실행
    const pythonProcess = spawn(
      "python",
      ["-m", "src.08_scheduler", "run_now"],
      {
        cwd: projectRoot,
        shell: true,
      }
    );

    let stdout = "";
    let stderr = "";

    pythonProcess.stdout.on("data", (data) => {
      stdout += data.toString();
      console.log(`[cron] ${data}`);
    });

    pythonProcess.stderr.on("data", (data) => {
      stderr += data.toString();
      console.error(`[cron error] ${data}`);
    });

    // 프로세스 완료 대기
    const exitCode = await new Promise<number>((resolve) => {
      pythonProcess.on("close", (code) => {
        resolve(code ?? 1);
      });
    });

    console.log("[cron] 스케줄 수집 완료:", new Date().toISOString());

    if (exitCode !== 0) {
      return NextResponse.json(
        {
          success: false,
          error: "Scheduled collection failed",
          details: stderr || stdout,
          exitCode,
          timestamp: new Date().toISOString(),
        },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "스케줄 수집 완료",
      timestamp: new Date().toISOString(),
      output: stdout.slice(-500), // 마지막 500자만
    });
  } catch (error) {
    console.error("[cron] Error:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to run scheduled collection",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
