import server

Extern_PC = server.ESXiHypervisor("135.39.70.72", "root", "ChangeMe")

print Extern_PC.status()

if Extern_PC.shutdown() == "ERROR":
	Extern_PC.force_shutdown()

print Extern_PC.status()