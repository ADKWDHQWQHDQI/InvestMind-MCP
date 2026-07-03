import subprocess
import json
import time
import sys
import os

def test_live_mcp_stdio():
    # Make sure we use the correct slash depending on OS
    python_exe = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"
        
    print(f"Starting InvestMind MCP Server via: {python_exe} src/main.py --transport stdio")
    
    # Start subprocess
    process = subprocess.Popen(
        [python_exe, "src/main.py", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Let process initialize
    time.sleep(1.0)
    
    try:
        # 1. Send Initialize Request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        
        print("\n[Client -> Server] Sending 'initialize' request...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        init_response = process.stdout.readline()
        print("[Server -> Client] Received:", init_response.strip())
        
        # 2. Send Hello Tool Call Request
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "hello_mcp",
                "arguments": {}
            }
        }
        
        print("\n[Client -> Server] Sending 'hello_mcp' tool call...")
        process.stdin.write(json.dumps(tool_request) + "\n")
        process.stdin.flush()
        
        # Read response
        tool_response = process.stdout.readline()
        print("[Server -> Client] Received:", tool_response.strip())
        
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"\nError occurred during interaction: {e}")
        process.terminate()
        stdout, stderr = process.communicate()
        if stderr:
             print("\n[Server Stderr LOG]:\n", stderr.strip())
        if stdout:
             print("\n[Server Stdout LOG]:\n", stdout.strip())
    print("\nMCP stdio validation complete!")

if __name__ == "__main__":
    test_live_mcp_stdio()
