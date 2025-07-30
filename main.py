import os


def main():
    print("Hello from memory-mcp!")
    print(f"Curent Path:{os.getcwd()}")


if __name__ == "__main__":
    main()
    file_dir = os.path.dirname(os.path.abspath(__file__)) 
    print(f"filedir={file_dir}")
    os.chdir(file_dir)
    print(f"Current Path: {os.getcwd()}")

    from mcp.server.fastmcp import FastMCP
