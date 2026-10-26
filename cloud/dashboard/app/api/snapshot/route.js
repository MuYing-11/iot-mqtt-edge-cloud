import { getHub } from "@/lib/hub";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  return Response.json(getHub().state);
}
