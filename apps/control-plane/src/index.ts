import { createApp } from "./app.js";

async function main(): Promise<void> {
  const app = createApp();
  const port = Number(process.env.PORT ?? 8100);
  const host = process.env.HOST ?? "0.0.0.0";

  try {
    await app.listen({ port, host });
    app.log.info(`control-plane listening on ${host}:${port}`);
  } catch (error) {
    app.log.error(error);
    process.exit(1);
  }
}

void main();

