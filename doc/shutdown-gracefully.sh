#!/bin/sh

VMID=$(/usr/bin/vim-cmd vmsvc/getallvms | grep -v Vmid | awk '{print $1}')

AVMIDS=""
for i in $VMID
do
  STATE=$(/usr/bin/vim-cmd vmsvc/power.getstate $i | tail -1 | awk '{print $2}')
  if [ $STATE == on ]
  then
    /usr/bin/vim-cmd vmsvc/power.shutdown $i
    AVMIDS="$AVMIDS $i"
  fi
done

while [ -n "$AVMIDS" ]; do
  echo "AVMIDS: $AVMIDS"
  for i in $AVMIDS
  do
    STATE=$(/usr/bin/vim-cmd vmsvc/power.getstate $i | tail -1 | awk '{print $2}')
    if [ "$STATE" == off ]; then
      echo "VMID down: $i"
      AVMIDS=$(echo "$AVMIDS" | sed "s/\b$i\b//g")
    fi
  done
  AVMIDS=$(echo "$AVMIDS" | sed "s/ */ /g" | sed "s/^ *//g" | sed "s/ *$//g")
done

echo "All done. Powering off"
/sbin/shutdown.sh
/sbin/poweroff

