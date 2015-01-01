import sqlite3
import logging
import argparse
import sys

# config
DATABASE = 'doorlock.db'

# parse arguments
parser = argparse.ArgumentParser()
parser_subs = parser.add_subparsers(help='entity help', dest='entity')

parser_person = parser_subs.add_parser('person', help='a help')
parser_person_subs = parser_person.add_subparsers(help='sub-command help', dest='action')
parser_person_create = parser_person_subs.add_parser('create', help='create a new person')
parser_person_create.add_argument("name")

parser_token = parser_subs.add_parser('token', help='a help')
parser_token_subs = parser_token.add_subparsers(help='sub-command help', dest='action')
parser_token_add = parser_token_subs.add_parser('add', help='add a new token')
parser_token_add.add_argument("person")
parser_token_add.add_argument("token")
parser_token_add.add_argument("pin")


args = parser.parse_args()

# get logger
logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)
logger = logging.getLogger("doorlock")
logger.info("Starting doorlock backend")

# instantiate db connection
conn = sqlite3.connect(DATABASE)
c = conn.cursor()
logger.debug("Database opened")

if args.entity == "person":
	if args.action == "create":
		t = (args.name,)
		c.execute("SELECT * FROM dl_persons WHERE name=?;",t)
		if c.fetchone() != None:
			print "Person '" + args.name + "' already exists."
			sys.exit(1)
		
		c.execute("INSERT INTO dl_persons(name, disabled) VALUES (?, '0');",t)
		if c.rowcount == 1:
			print "Person '" + args.name + "' successfully created."
		else:
			print "Error while creating person'" + args.name + "'."
elif args.entity == "token":
	if args.action == "add":

		t = (args.person,)
                c.execute("SELECT id FROM dl_persons WHERE name=?;",t)
                row = c.fetchone()
		if row == None:
                        print "Person '" + args.person + "' does not exist."
                        sys.exit(1)
		
		t = (args.token,args.pin,)
                c.execute("SELECT * FROM dl_tokens WHERE token=? AND pin =?;",t)
                if c.fetchone() != None:
                        print "Token already exists."
                        sys.exit(1)

		t = (row[0],args.token,args.pin,)
                c.execute("INSERT INTO dl_tokens(person_id, token, pin) VALUES (?,?,?);",t)
                if c.rowcount == 1:
                        print "Token for '" + args.person + "' successfully created."
                else:
                        print "Error while adding token."


conn.commit()
conn.close()
