create table bmnodes (
	id	integer primary key autoincrement not null,
	ip	text,
	port	integer,
	last_seen	integer,
	priority	integer default 0,
	cores	integer
);
create unique index if not exists node_id on bmnodes(ip,port);

create table comps (
	id	integer primary key autoincrement not null,
	temp_id	text	default NULL,
	comp_id	text	default NULL,
	ipsrc	text	default NULL,
	sport	integer,
	ipdst	text	default NULL,
	dport	integer,
	compobj	blob	default NULL
);
create unique index if not exists comp_id on comps(comp_id,ipsrc,sport,temp_id);

create table blocks (
	id	integer primary key autoincrement not null,
	name text default NULL,
	info blob default NULL
);
create unique index if not exists name on blocks(name);
