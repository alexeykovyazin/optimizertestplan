SELECT COUNT(*) FROM postHistory as ph, comments as c, posts as p WHERE c.PostId = p.Id AND ph.PostId = p.Id
