export async function GET() {
  return Response.json({ status: "ok" });
}

export async function POST(request: Request) {
  const body = await request.json();
  return Response.json({ received: body });
}
