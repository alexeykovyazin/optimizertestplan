create database 'probe6' user SYSDBA page_size 8192;
create table fn(id int, v varchar(20));
create table ln(id int, v varchar(20));
insert into fn values(0,'Al');
insert into fn values(1,'Bo');
insert into fn values(2,'Ann');
insert into fn values(3,'Eva');
insert into fn values(4,'John');
insert into fn values(5,'Mary');
insert into fn values(6,'Peter');
insert into fn values(7,'Maria');
insert into fn values(8,'Olga');
insert into fn values(9,'Ivan');
insert into fn values(10,'Sergei');
insert into fn values(11,'Michael');
insert into fn values(12,'Anna');
insert into fn values(13,'Robert');
insert into fn values(14,'Elizabeth');
insert into fn values(15,'Christopher');
insert into fn values(16,'Alexander');
insert into fn values(17,'Dmitry');
insert into fn values(18,'Svetlana');
insert into fn values(19,'Jean-Pierre');
insert into ln values(0,'Li');
insert into ln values(1,'Wu');
insert into ln values(2,'Kim');
insert into ln values(3,'Lee');
insert into ln values(4,'Smith');
insert into ln values(5,'Brown');
insert into ln values(6,'Ivanov');
insert into ln values(7,'Petrova');
insert into ln values(8,'Garcia');
insert into ln values(9,'Miller');
insert into ln values(10,'Nguyen');
insert into ln values(11,'Rossi');
insert into ln values(12,'Dubois');
insert into ln values(13,'Johnson');
insert into ln values(14,'Martinez');
insert into ln values(15,'Kowalski');
insert into ln values(16,'Andersson');
insert into ln values(17,'Takahashi');
insert into ln values(18,'Rodriguez');
insert into ln values(19,'Hernandez');
insert into ln values(20,'Schmidt');
insert into ln values(21,'Wilson');
insert into ln values(22,'Moore');
insert into ln values(23,'Schwarzenegger');
commit;
create table pn(
  id int,
  nm varchar(80) character set utf8,
  nn varchar(80) character set none,
  nc char(80) character set utf8,
  nb blob sub_type text character set utf8);
set term ^;
execute block as
  declare i int = 0;
  declare r int; declare r2 int; declare f int; declare l int; declare l2 int;
  declare m int; declare s int;
  declare fv varchar(20); declare lv varchar(20); declare lv2 varchar(20);
  declare nm varchar(80);
begin
  while (i < 200000) do
  begin
    r = mod(i * 7919 + 13, 1000);
    f = (r * r) / 50000;
    r2 = mod(i * 104729 + 7, 1000);
    l = (r2 * r2) / 41667;
    select v from fn where id = :f into fv;
    select v from ln where id = :l into lv;
    nm = fv;
    m = mod(i * 31 + 3, 40);
    if (m < 26) then nm = nm || ' ' || ascii_char(65 + m) || '.';
    nm = nm || ' ' || lv;
    if (mod(i, 11) = 0) then
    begin
      l2 = mod(i / 11, 24);
      select v from ln where id = :l2 into lv2;
      nm = nm || '-' || lv2;
    end
    s = mod(i * 17, 10);
    if (s = 0) then nm = nm || ' Jr.';
    else if (s = 1) then nm = nm || ' III';
    insert into pn values(:i, :nm, :nm, :nm, :nm);
    i = i + 1;
  end
end^
set term ;^
commit;
alter database add extended statistics;
commit;
alter database refresh statistics for table pn;
commit;
set list on;
select STAT$FIELD_NAME, STAT$NDISTINCT, STAT$SAMPLE_SIZE, STAT$MCV_ROWS, STAT$HIST_ROWS,
  STAT$LEN_COUNT, STAT$LEN_SUM, STAT$LEN_MIN, STAT$LEN_MAX, STAT$LEN_BOUNDS_TEXT
from STAT$COLUMNS where STAT$RELATION_NAME = 'PN' order by 1;
set list off;
select char_length(nm) L, count(*) from pn group by 1 order by 1;
select count(distinct nm), avg(char_length(nm)) from pn;
