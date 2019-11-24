from collections import namedtuple

updated_bill_info = namedtuple('updated_bill_info', ['id', 'last_action_name'])

a = {'education': [[], [updated_bill_info(id='201720180SB220', last_action_name='')]], 'bills': [[], []], 'any': [[], [updated_bill_info(id='201720180SB1215', last_action_name='Chaptered Date')]], 'change': [[], [updated_bill_info(id='201720180SB1215', last_action_name='Chaptered Date'), updated_bill_info(id='201720180SB1401', last_action_name='')]], 'home': [[], [updated_bill_info(id='201720180AB614', last_action_name=''), updated_bill_info(id='201720180SB1206', last_action_name='')]]}
#a = {'chinese': [[], []], 'education': [[], []]}


print(any([bool(v) for val in list(a.values()) for v in val]))