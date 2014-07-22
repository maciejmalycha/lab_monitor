read INPUT

while [ "$INPUT" != "exit" ]
do
	python2.6 client.py "$INPUT"
	read INPUT
done 
