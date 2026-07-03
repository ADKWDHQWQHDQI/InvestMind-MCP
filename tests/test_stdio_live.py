import subprocess
import json
import time
import sys
import os

def test_live_mcp_stdio():
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
        init_response_raw = process.stdout.readline()
        print("[Server -> Client] Received:", init_response_raw.strip())
        
        # Assertions on Initialization Response
        init_data = json.loads(init_response_raw)
        assert init_data["jsonrpc"] == "2.0"
        assert init_data["id"] == 1
        assert "result" in init_data
        assert "protocolVersion" in init_data["result"]
        assert init_data["result"]["serverInfo"]["name"] == "InvestMind"
        print("OK: 'initialize' response assertions passed!")
        
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
        tool_response_raw = process.stdout.readline()
        print("[Server -> Client] Received:", tool_response_raw.strip())
        
        # Assertions on Tool Call Response
        tool_data = json.loads(tool_response_raw)
        assert tool_data["jsonrpc"] == "2.0"
        assert tool_data["id"] == 2
        assert "result" in tool_data
        assert tool_data["result"]["isError"] is False
        assert tool_data["result"]["content"][0]["text"] == "Hello Sandeep! MCP is working."
        print("OK: 'hello_mcp' tool execution assertions passed!")
        
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"\nERROR: Error occurred during validation: {e}")
        process.terminate()
        stdout, stderr = process.communicate()
        if stderr:
             print("\n[Server Stderr LOG]:\n", stderr.strip())
        if stdout:
             print("\n[Server Stdout LOG]:\n", stdout.strip())
        sys.exit(1)
        
    print("\nSUCCESS: MCP stdio validation complete! All integration assertions passed.")


if __name__ == "__main__":
    test_live_mcp_stdio()
