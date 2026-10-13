-- STATS simplified dataset (End-to-End CardEst Benchmark, упрощённый дамп Stack Exchange)
-- Конфигурация индексов: pk (только первичные ключи).
-- Порт под Firebird 5. Отступление от оригинала (PostgreSQL):
--   SERIAL -> INTEGER NOT NULL; зарезервированные слова Firebird "Date" и "Count"
--   квотированы (в запросах должны квотироваться так же, см. port_notes в манифесте).

CREATE TABLE users (
  Id INTEGER NOT NULL PRIMARY KEY,
  Reputation INTEGER,
  CreationDate TIMESTAMP,
  Views INTEGER,
  UpVotes INTEGER,
  DownVotes INTEGER
);

CREATE TABLE posts (
  Id INTEGER NOT NULL PRIMARY KEY,
  PostTypeId SMALLINT,
  CreationDate TIMESTAMP,
  Score INTEGER,
  ViewCount INTEGER,
  OwnerUserId INTEGER,
  AnswerCount INTEGER,
  CommentCount INTEGER,
  FavoriteCount INTEGER,
  LastEditorUserId INTEGER
);

CREATE TABLE postLinks (
  Id INTEGER NOT NULL PRIMARY KEY,
  CreationDate TIMESTAMP,
  PostId INTEGER,
  RelatedPostId INTEGER,
  LinkTypeId SMALLINT
);

CREATE TABLE postHistory (
  Id INTEGER NOT NULL PRIMARY KEY,
  PostHistoryTypeId SMALLINT,
  PostId INTEGER,
  CreationDate TIMESTAMP,
  UserId INTEGER
);

CREATE TABLE comments (
  Id INTEGER NOT NULL PRIMARY KEY,
  PostId INTEGER,
  Score SMALLINT,
  CreationDate TIMESTAMP,
  UserId INTEGER
);

CREATE TABLE votes (
  Id INTEGER NOT NULL PRIMARY KEY,
  PostId INTEGER,
  VoteTypeId SMALLINT,
  CreationDate TIMESTAMP,
  UserId INTEGER,
  BountyAmount SMALLINT
);

CREATE TABLE badges (
  Id INTEGER NOT NULL PRIMARY KEY,
  UserId INTEGER,
  "Date" TIMESTAMP
);

CREATE TABLE tags (
  Id INTEGER NOT NULL PRIMARY KEY,
  "Count" INTEGER,
  ExcerptPostId INTEGER
);
