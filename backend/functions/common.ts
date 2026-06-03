import { readFile } from "node:fs/promises";
import { Client } from "@modelcontextprotocol/sdk/client";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

async function callVisionMcp(prompt: string, imagePath: string, sampleImage?: string | string[]): Promise<void> {

    const imageBuffer = await readFile(imagePath);
    const imageBase64 = imageBuffer.toString("base64");
    const transport = new StreamableHTTPClientTransport(new URL("http://localhost:6000/mcp"));
    const client = new Client({name: "vision-client", version: "1.0.0",});

    await client.connect(transport);

    const result = await client.callTool({
        name: "Vision",
        arguments: {
            prompt,
            image: imageBase64,
            sample_image: sampleImage,
        },
    });

    console.dir(result, { depth: null });

    await client.close();
}

async function main(): Promise<void> {
    await callVisionMcp(
        "Is Playwright displayed?",
        "C:/Users/medvi/OneDrive/Desktop/bini-ai/data/images/main.png",
    );
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});