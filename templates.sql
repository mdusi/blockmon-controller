create table templatedefs (
	id	integer primary key autoincrement not null,
	temp_id	text,
	template	text
);
create unique index if not exists template_id on templatedefs(temp_id);

