"""wcpatch.py - the research prototype of the worst case rule for the join method choice.
Patches the working tree of hqbird-impropt (the base branch or the PR 42 branch). Never commit the result.
The rule: the hash join is taken when
    weight * ln(worstLoop / worstHash) >= (1 - weight) * ln(hashCost / loopCost)
where the worst costs are priced at the prefix cardinality multiplied by the worst / average ratios of the
keys of the prior non-unique joins. The parameters and the key degrees come from E:/fbdata/wc_risk.txt."""
R = 'E:/Projects_Big/hqbird-impropt/src/jrd/optimizer/'


def load(name):
    s = open(R + name, encoding='utf-8', newline='').read()
    return s, ('\r\n' if '\r\n' in s else '\n')


def save(name, s):
    open(R + name, 'w', encoding='utf-8', newline='').write(s)


def sub(s, nl, old, new, where):
    old = old.replace('\n', nl)
    new = new.replace('\n', nl)
    assert s.count(old) == 1, (where, s.count(old))
    return s.replace(old, new, 1)


# ---- Optimizer.h
s, nl = load('Optimizer.h')
assert 'worstRatio' not in s
s = sub(s, nl, '\t\t\tfanout = false;\n', '\t\t\tfanout = false;\n\t\t\tworstRatio = 1.0;\n', 'reset')
s = sub(s, nl, '\t\tbool fanout = false;\t\t// joined by a non-unique retrieval\n',
        '\t\tbool fanout = false;\t\t// joined by a non-unique retrieval\n'
        '\t\tdouble worstRatio = 1.0;\t// WCRISK: worst / average rows per key of this join\n', 'field')
save('Optimizer.h', s)

# ---- InnerJoin.cpp
s, nl = load('InnerJoin.cpp')
pr42 = 'getPageMissCost' in s
bs = chr(92)

loader = '''#include "../extstat/ext_stats.h"

// WCRISK prototype (research only, not for a commit): the method choice by
// the worst case of the prefix cardinality instead of the constant risk
#include <map>
#include <string>
#include <cstdio>
#include <cstdlib>
#include <cmath>

namespace
{
	struct WcRisk
	{
		int mode = 0;			// 0 - constant risk, 1 - max degree, 2 - size-biased degree, 3 - fixed ratio
		double weight = 0.5;	// weight of the worst case in the comparison
		double defRatio = 4.0;	// worst / average of an unknown key
		double cap = 0;			// limit of the prefix ratio, 0 - none
		int unique = 0;			// 1 - the rule applies to the unique lookups too
		std::map<std::string, double> ratios;
	};

	const WcRisk& wcRisk()
	{
		static const WcRisk instance = []()
		{
			WcRisk r;
			const char* name = getenv("FB_WC_RISK");
			FILE* f = fopen(name ? name : "E:/fbdata/wc_risk.txt", "r");

			if (f)
			{
				if (fscanf(f, "%d %lf %lf %lf %d", &r.mode, &r.weight, &r.defRatio, &r.cap, &r.unique) != 5)
					r.mode = 0;

				char rel[256];
				int idx;
				double avg, sb, mx;

				while (fscanf(f, "%255s %d %lf %lf %lf", rel, &idx, &avg, &sb, &mx) == 5)
				{
					char key[300];
					snprintf(key, sizeof(key), "%s.%d", rel, idx);
					const double worst = (r.mode == 1) ? mx : (r.mode == 2) ? sb : avg * r.defRatio;
					r.ratios[key] = (avg > 0 && worst > avg) ? worst / avg : 1.0;
				}

				fclose(f);
			}

			return r;
		}();

		return instance;
	}
}
'''
s = sub(s, nl, '#include "../extstat/ext_stats.h"\n', loader, 'loader')

fan = '\tjoinedStreams[position].fanout = position && !candidate->unique && !floorLimited;\n'
fanNew = fan + '''
	// WCRISK: worst / average rows per key of this join
	joinedStreams[position].worstRatio = 1.0;

	if (joinedStreams[position].fanout)
	{
		const WcRisk& wc = wcRisk();
		double wcKeyRatio = wc.defRatio;
		const auto wcRelation = csb->csb_rpt[stream->number].csb_relation;

		if (wc.mode != 3 && wcRelation && candidate->scratch && candidate->scratch->index)
		{
			char key[300];
			snprintf(key, sizeof(key), "%s.%d", wcRelation->rel_name.c_str(),
				(int) candidate->scratch->index->idx_id);

			const auto it = wc.ratios.find(key);

			if (it != wc.ratios.end())
				wcKeyRatio = it->second;
		}

		joinedStreams[position].worstRatio = wcKeyRatio;
	}
'''
s = sub(s, nl, fan, fanNew, 'fanout')

missLoop = ' +\n\t\t\t\toptimizer->getPageMissCost(loopPageAccesses, candidate->pageUniverse, wcCard)' if pr42 else ''
missHash = ' +\n\t\t\t\toptimizer->getPageMissCost(stream->basePageAccesses, stream->basePageUniverse, 1)' if pr42 else ''

cond = '\t\tif (hashCost <= loopRiskCost &&\n'
condNew = '''		// WCRISK: the loss of the loop in the worst case against the loss of the
		// hash join in the estimated case
		bool wcChooseHash = hashCost <= loopRiskCost;
		const WcRisk& wcr = wcRisk();

		if (wcr.mode)
		{
			double wcRatio = 1.0;

			if (joinedStreams[position].fanout || wcr.unique)
			{
				for (unsigned i = 1; i < position; i++)
				{
					if (joinedStreams[i].fanout)
						wcRatio *= joinedStreams[i].worstRatio;
				}
			}

			if (wcr.cap > 0 && wcRatio > wcr.cap)
				wcRatio = wcr.cap;

			const double wcCard = cardinality * wcRatio;
			const double wcLoop = Optimizer::getLoopJoinCost(candidate->cost, wcCard)MISSLOOP;
			const double wcHash = (hashedRows > HashJoin::maxCapacity() ?
				Optimizer::getBatchHashJoinCost(stream->baseCost, wcCard,
												hashCardinality, currentCardinality,
												bhjSpillShare) :
				Optimizer::getHashJoinCost(stream->baseCost, wcCard,
										   hashCardinality, currentCardinality,
										   hjSpillShare))MISSHASH;

			const double tiny = 1e-9;

			wcChooseHash = wcr.weight * log(MAX(wcLoop, tiny) / MAX(wcHash, tiny)) >=
				(1.0 - wcr.weight) * log(MAX(hashCost, tiny) / MAX(loopCost, tiny));
		}

		if (wcChooseHash &&
'''.replace('MISSLOOP', missLoop).replace('MISSHASH', missHash)
s = sub(s, nl, cond, condNew, 'cond')
save('InnerJoin.cpp', s)
print('patched, pr42 =', pr42)
