import random


class Condition:
    def match(self, alisa):
        raise NotImplemented("")


class Dialog:
    def __init__(self):
        self.conditionFuncs = {
            'on_intent': self.intent_match,
            'call_handler': self.next_handler_match
        }

    def handle_dialog(self, alisa):
        if alisa.is_new_session():
            return self.greetings(alisa)

        handler = self.match(alisa)

        if handler:
            handler = getattr(self, handler, self.fallback)
            return handler(alisa)
        else:
            return self.fallback(alisa)

    def greetings(self, alisa):
        pass

    def help(self, alisa):
        pass

    def fallback(self, alisa):
        pass

    def intent_match(self, alisa, context):
        return alisa.has_intent(context['name'])

    def next_handler_match(self, alisa, context):
        return True

    def on_intent(self, intent_name):
        return 'on_intent', {'name': intent_name}

    def one_of(self, lines):
        return random.choice(lines)

    def match(self, alisa):
        funcs = self.conditionFuncs
        for transition in alisa.get_transitions():
            condition = transition.get('condition', {})
            if funcs.get(condition.get('name')):
                if funcs.get(condition.get('name'))(alisa, condition.get('context')):
                    return transition.get('handler')
        return None


class Alisa:
    def __init__(self, request, response):
        self.event, self.answer, self.response = request.json, response['response'], response
        self.intents = self.event.get('request', {}).get('nlu', {}).get('intents', {})
        self.command = self.event.get('request', {}).get('command')
        self.state_session = self.event.get('state', {}).get('session', {})
        self.application_state = self.event.get('state', {}).get('application', {})
        self.user_state = self.event.get('state', {}).get('user', {})
        self.original_utterance = self.event.get('request', {}).get('original_utterance')

    def is_new_session(self):
        return self.event['session']['new']

    def get_state(self):
        return self.event['state']

    def get_intent_slot_value(self, intent, slot):
        return self.intents.get(intent, {}).get('slots', {}).get(slot, {}).get('value', {})

    def get_original_utterance(self):
        return self.original_utterance

    def add_to_session_state(self, key, value):
        self.response['session_state'] = self.response.get('session_state', {})
        self.response['session_state'][key] = value

    def update_user_state(self, key, value):
        self.response['user_state_update'] = self.response.get('user_state_update', {})
        self.response['user_state_update'][key] = value

    def get_session_object(self, key):
        return self.state_session.get(key, {})

    def get_user_state_object(self, key):
        return self.user_state.get(key, {})

    def end_session(self):
        self.answer['end_session'] = True

    def voice_button(self, condition, handler):
        matcher, context = condition
        self.add_transition(matcher, context, handler)

    def suggest(self, title, handler, url=None, payload=None):
        if payload is None:
            payload = {}
        self.button(title, handler, True, url, payload)

    def button(self, title, handler, hide=False, url=None, payload=None):
        if payload is None:
            payload = {}
        self.answer['buttons'] = self.answer.get('buttons', [])
        payload["__transition__"] = {'condition': {"name": 'call_handler', "context": {}}, 'handler': handler}
        button = {"title": title,
                  "payload": payload,
                  "hide": hide}
        if url:
            button["url"] = url
        self.answer['buttons'].append(button)

    def call_after(self, handler):
        self.add_transition('call_handler', {}, handler)

    def add_transition(self, name, context, handler):
        self.response['session_state'] = self.response.get('session_state', {})
        self.response['session_state']['__transitions__'] = self.response.get('session_state', {}).get(
            '__transitions__', [])
        self.response['session_state']['__transitions__'].append(
            {'condition': {"name": name, "context": context}, 'handler': handler})

    def get_button_payload_value(self, value):
        return self.event.get('request', {}).get('payload', {}).get(value, {})

    def get_transitions(self):
        transitions = self.state_session.get('__transitions__', [])
        if self.event.get('request', {}).get('type', '') == 'ButtonPressed':
            button_transition = self.event.get('request', {}).get('payload', {}).get('__transition__')
            if button_transition:
                transitions.append(button_transition)
        return transitions

    def tts_with_text(self, tts):
        self.answer['text'] = self.answer.get('text', '') + tts
        self.answer['tts'] = self.answer.get('tts', '') + tts

    def text(self, tts):
        self.answer['text'] = self.answer.get('text', '') + tts

    def tts(self, tts):
        self.answer['tts'] = self.answer.get('tts', '') + tts

    def has_intent(self, intent):
        return self.intents.get(intent)
