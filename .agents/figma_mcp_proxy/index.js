const { SSEClientTransport } = require("@modelcontextprotocol/sdk/client/sse.js");
const readline = require("readline");

async function run() {
  // Use the endpoint and token provided by the user
  const transport = new SSEClientTransport(new URL("https://mcp.figma.com/mcp"), {
    requestInit: {
      headers: {
        "X-Figma-Token": process.env.FIGMA_API_KEY || "REMOVED_SECRET"
      }
    }
  });

  transport.onmessage = (msg) => {
    // Write message to stdout as JSON-RPC with newline
    process.stdout.write(JSON.stringify(msg) + "\n");
  };
  
  transport.onclose = () => {
    process.exit(0);
  };
  
  transport.onerror = (err) => {
    console.error("Transport error:", err);
  };

  await transport.start();

  // Read stdin line by line and send to transport
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  rl.on("line", async (line) => {
    if (line.trim()) {
      try {
        const msg = JSON.parse(line);
        await transport.send(msg);
      } catch (e) {
        console.error("Error processing line:", e);
      }
    }
  });
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
