SELECT COUNT(*) FROM votes as v WHERE v.BountyAmount>=0 AND v.BountyAmount<=300 AND v.CreationDate>=CAST('2010-07-29 00:00:00' AS TIMESTAMP)
