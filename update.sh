#!/usr/bin/env zsh

OLD=$1

NEW=`date +'%Y-%m-%d'`.db

function printerror { print -P "[%F{red}%BError%b%f] $1" }
function printinfo  { print -P "[%F{white}%BInfo%b%f] $1" }

[[ $# != 1 ]] && {
    printerror 'Wrong parameters'
    print "Usage: $0 OLD_DB"
    exit 1    
}

[[ ! -f $OLD ]] && {
    printerror "$OLD is not a file!"
    exit 1
}

[[ $OLD -ef $NEW ]] && {
    printerror 'You made an archive today. Change the name of the previous one.'
    exit 1
}

cp $OLD $NEW
printinfo 'Updating staging database..'
./mvs-dump.py $NEW 12000 || {
    printerror 'Update failed.. Exiting.'
    exit 2
}

# {{{ Print products
{
    printinfo 'Printing product diff..'
    diff -c =(sqlite3 $OLD 'select * from products;') =(sqlite3 $NEW 'select * from products;')
}
# }}}

printinfo 'Press any key to continue.'
read -sk1

# {{{ Print files
{
    printinfo 'Printing file diff..'
    diff -c =(sqlite3 $OLD 'select * from files;') =(sqlite3 $NEW 'select * from files;')
}
# }}}

printinfo 'Do you want to keep the new database? (y/N)'
read -sq || {
    printinfo 'Alright. Cleaning up.'
    rm $NEW
    exit
}

printinfo "Keeping database $NEW.."
printinfo "Compressing.."
gzip -k9 $NEW
printinfo 'Done! Database compressed into .gz'
