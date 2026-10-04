import json
import tempfile
import unittest
from types import SimpleNamespace
from core import execute, run_agent
from storage import Storage

class Message:
    def __init__(self, value): self.value = value
    def model_dump(self, **kwargs): return self.value

class FakeCloud:
    def __init__(self):
        self.calls = []
        self.chat = SimpleNamespace(completions=self)
    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            message = {'role':'assistant', 'tool_calls':[{'id':'a1','type':'function',
                'function':{'name':'calculate_square_foot','arguments':'{"length":12.5,"width":2}'}}]}
        else:
            assert kwargs['messages'][-1]['tool_call_id'] == 'a1'
            assert json.loads(kwargs['messages'][-1]['content'])['area'] == 25
            message = {'role':'assistant', 'content':'25 square feet.'}
        return SimpleNamespace(choices=[SimpleNamespace(message=Message(message))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))

class FakeLocal:
    def __init__(self): self.calls = 0
    def chat(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            msg = {'role':'assistant','content':'','tool_calls':[{'function':{
                'name':'calculate_square_foot', 'arguments':{'length':12.5,'width':2}}}]}
        else:
            assert kwargs['messages'][-1]['tool_name'] == 'calculate_square_foot'
            msg = {'role':'assistant','content':'25 square feet.'}
        return {'message':msg,'prompt_eval_count':10,'eval_count':5}

class Tests(unittest.TestCase):
    def test_tools_and_invalid_inputs(self):
        self.assertEqual(json.loads(execute('calculate_square_foot', {'length':1.5,'width':2}))['area'], 3)
        for args in ({'length':-1,'width':2}, {'length':float('inf'),'width':2}, {'length':True,'width':2}):
            self.assertIn('error', json.loads(execute('calculate_square_foot', args)))
        self.assertIn('error', json.loads(execute('run_shell', {'command':'echo hello'})))
        self.assertIn('error', json.loads(execute('web_search', {'query':'today'})))

    def test_both_tool_loops(self):
        history = [{'role':'user','content':'Area of 12.5 by 2?'}]
        for engine, client in [('cloud',FakeCloud()),('local',FakeLocal())]:
            answer, usage = run_agent(engine, history, client=client)
            self.assertEqual(answer, '25 square feet.')
            self.assertEqual(usage['input_tokens'], 20)

    def test_private_storage_auth_feedback_reset(self):
        with tempfile.TemporaryDirectory() as path:
            db = Storage(path+'/test.db')
            db.register('alice','a long test password')
            db.register('bob','a long test password')
            self.assertTrue(db.verify('alice','a long test password'))
            self.assertFalse(db.verify('alice','wrong'))
            self.assertFalse(db.verify('absent','a long test password'))
            message = db.save('alice','cloud','assistant','Private')
            db.save('alice','local','assistant','Local')
            self.assertEqual(db.load('bob','cloud'), [])
            self.assertEqual(len(db.load('alice','cloud')), 1)
            with self.assertRaises(ValueError): db.feedback('bob',message,1)
            db.feedback('alice',message,1)
            db.feedback('alice',message,0)
            db.clear('alice','cloud')
            self.assertEqual(db.load('alice','cloud'), [])
            self.assertEqual(len(db.load('alice','local')), 1)

if __name__ == '__main__': unittest.main()
