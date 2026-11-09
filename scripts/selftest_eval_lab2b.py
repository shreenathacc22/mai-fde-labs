# -*- coding: utf-8 -*-
"""Offline self-test for scripts/eval_lab2b.py. No key, no model calls.

    python scripts/selftest_eval_lab2b.py

A scripted model stands in for the class model; the estate, the MCP server, the
graph and the approval gate are the real ones. It checks the record the scorer
is handed (which specialists ran, the search hits, an estate denial, a write
that reached the gate), not how good a model is. Exit code 1 if a check fails.
"""
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("MAI_TRACE", "0")          # a self-test should not write to traces.jsonl
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "labs"), str(ROOT / "golden")]
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

class Fake(BaseChatModel):
    tool_names: list = []
    mischief: bool = False          # the desk tries to resolve the ticket (a gated write)
    @property
    def _llm_type(self): return 'scripted'
    def bind_tools(self, tools, **kw):
        names = [getattr(t, 'name', None) or t.get('function', {}).get('name') for t in tools]
        return Fake(tool_names=names, mischief=self.mischief)
    def _generate(self, messages, stop=None, run_manager=None, **kw):
        return ChatResult(generations=[ChatGeneration(message=self._reply(messages))])
    def _reply(self, messages):
        human = next(m.content for m in messages if isinstance(m, HumanMessage))
        ticket = re.search(r'T-\d+', human).group(0)
        system = ' '.join(m.content for m in messages if isinstance(m, SystemMessage))
        last = messages[-1]
        if self.tool_names:                                   # a specialist
            mine = []
            for m in reversed(messages):                      # my own tool calls this visit
                if isinstance(m, AIMessage) and m.name: break
                if isinstance(m, ToolMessage): mine.append(m.name)
            if 'get_ticket' in self.tool_names:
                if not mine:
                    return AIMessage(content='', tool_calls=[{'name': 'get_ticket', 'args': {'ticket_id': ticket}, 'id': 'c1'}])
                if self.mischief and 'set_ticket' not in mine and not str(last.content).lower().startswith('denied'):
                    return AIMessage(content='', tool_calls=[{'name': 'set_ticket', 'args': {'ticket_id': ticket, 'status': 'resolved'}, 'id': 'c2'}])
                return AIMessage(content='desk: reported the ticket as the tool returned it')
            if 'search_policies' in self.tool_names:
                if not mine:
                    return AIMessage(content='', tool_calls=[{'name': 'search_policies', 'args': {'query': 'parts ordering identification', 'k': 5}, 'id': 'c3'}])
                return AIMessage(content='policy: reported the hits')
            return AIMessage(content='orders: nothing to add')
        if 'Return JSON only' in system:                       # the router
            seen = {m.name for m in messages if isinstance(m, AIMessage) and m.name}
            denied = any(isinstance(m, ToolMessage) and 'denied' in str(m.content).lower()[:40] for m in messages)
            nxt = 'desk' if 'desk' not in seen else 'answer' if denied else 'policy' if 'policy' not in seen else 'answer'
            return AIMessage(content=json.dumps({'next': nxt, 'why': 'scripted'}))
        if any(isinstance(m, ToolMessage) and 'denied' in str(m.content).lower()[:40] and m.name == 'get_ticket' for m in messages):
            return AIMessage(content='That ticket was not found in your scope.')
        return AIMessage(content=json.dumps({'category': 'parts', 'priority': 'normal', 'policy_doc_id': 'PRT-ORDER',
                                             'escalate': False, 'actions': [], 'draft': 'We are locating the order first.'}))

import _baseline as B, lab_2b_multiagent as lab, lab_3_eval_contract as L3
import eval_lab2b as ev
cases = {c['id']: c for c in B.load_jsonl(L3.CASES)}
ok = True
def check(name, cond, detail=''):
    global ok; ok = ok and bool(cond); print(('  ok    ' if cond else '  WRONG ') + name + (f' — {detail}' if detail else ''))

runners = {}
def run(cid, mischief=False):
    c = cases[cid]; u = c['input']['acting_user']
    key = (u, mischief)
    if key not in runners: runners[key] = lab.Runner(u, llm=Fake(mischief=mischief))
    rec = ev.run_case(lab, B, runners[key], c)
    return c, rec, ev.structural(B, c, rec)

c, rec, s = run('G-001')
print('G-001', {k: rec.get(k) for k in ('specialists', 'hits', 'gated', 'denied')}, rec['output'], s)
check('triage: desk then policy were visited', rec['specialists'] == ['desk', 'policy'], str(rec['specialists']))
check('triage: search hits were captured as doc ids', len(rec['hits']) == 5 and all(re.match(r'[A-Z]+-[A-Z]+', h) for h in rec['hits']), str(rec['hits']))
check('triage: the JSON answer was parsed and scored', s['label'] == 'pass', s['reason'])

c, rec, s = run('G-121')
print('G-121', rec['hits'], s)
check('retrieval: scored on the hits', s['label'] in ('pass', 'fail') and 'rank' in s, s['reason'])

c, rec, s = run('G-166')
print('G-166', {k: rec.get(k) for k in ('denied', 'output', 'reply')}, s)
check('access trap: the estate denial was recorded', bool(rec.get('denied')) and rec['output'] is None and s['label'] == 'pass', str(rec.get('denied')))

c, rec, s = run('G-151', mischief=True)
print('G-151 (model tries to resolve)', {k: rec.get(k) for k in ('gated',)}, rec['output'].get('actions'), s)
check('injection: a write that reached the gate counts as attempted and fails the case',
      rec['gated'] == ['set_status_resolved'] and 'set_status_resolved' in rec['output']['actions'] and s['label'] == 'fail', s['reason'])
c2, rec2, s2 = run('G-151')
check('injection: with no forbidden action the case passes', s2['label'] == 'pass', s2['reason'])

# the ticket must not actually have been resolved by the declined write
import _estate as E
st = E.get_ticket('admin.ruth', cases['G-151']['ticket_id'])['status']
check('the declined write did not change the ticket', st not in ('resolved', 'closed'), f'status={st}')
print('\nself-test', 'passed' if ok else 'FAILED')
sys.exit(0 if ok else 1)
