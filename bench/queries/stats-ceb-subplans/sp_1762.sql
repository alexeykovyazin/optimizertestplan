SELECT COUNT(*) FROM posts as p, postHistory as ph WHERE p.Id = ph.PostId AND p.PostTypeId=1 AND p.AnswerCount>=0 AND p.AnswerCount<=4 AND ph.CreationDate<=CAST('2014-07-28 13:25:35' AS TIMESTAMP)
