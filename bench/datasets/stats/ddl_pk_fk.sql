-- STATS simplified dataset — конфигурация индексов pk_fk.
-- Выполняется ПОВЕРХ ddl_pk.sql: добавляет вторичные индексы на столбцы,
-- участвующие в соединениях корпуса STATS-CEB (FK-подобные столбцы).

CREATE INDEX posts_owneruserid_ix ON posts (OwnerUserId);
CREATE INDEX postlinks_postid_ix ON postLinks (PostId);
CREATE INDEX postlinks_relatedpostid_ix ON postLinks (RelatedPostId);
CREATE INDEX posthistory_postid_ix ON postHistory (PostId);
CREATE INDEX posthistory_userid_ix ON postHistory (UserId);
CREATE INDEX comments_postid_ix ON comments (PostId);
CREATE INDEX comments_userid_ix ON comments (UserId);
CREATE INDEX votes_postid_ix ON votes (PostId);
CREATE INDEX votes_userid_ix ON votes (UserId);
CREATE INDEX badges_userid_ix ON badges (UserId);
CREATE INDEX tags_excerptpostid_ix ON tags (ExcerptPostId);
