read INPUT

while [ "$INPUT" != "exit" ]
do
	python2.6 src/client.py "$INPUT"
	read INPUT
done 
