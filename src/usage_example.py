import server

Extern_PC = server.ESXiHypervisor("135.39.70.72", "root", "ChangeMe", 1)

print Extern_PC.status()

Extern_PC.shutdown()

print Extern_PC.status()