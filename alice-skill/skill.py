from __future__ import unicode_literals

import json
import logging
import random
import pandas as pd
from enum import Enum

from flask import Flask, request

from alisa import Alisa, Dialog

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)


# TODO: horoscope on date
# TODO: show protocole

class Sign(Enum):
    GEMINI = 'gemini'


class NeuroHoroscopeDialog(Dialog):

    def handle_dialog(self, alisa):
        sign = alisa.get_user_state_object('sign')
        reset_sign = alisa.get_button_payload_value('reset_sign')
        if sign and not reset_sign:
            return self.tell_horoscope_by_sign(alisa, Sign(sign))

        if alisa.is_new_session():
            return self.greetings(alisa)

        handler = self.match(alisa)

        if handler:
            handler = getattr(self, handler, self.fallback)
            return handler(alisa)
        else:
            return self.fallback(alisa)

    def tell_horoscope_by_sign(self, alisa: Alisa, sign: Sign):
        alisa.tts_with_text("Ваш гороскоп на сегодня: \n")
        alisa.tts("sil<[200]>")
        alisa.tts_with_text(self.get_random_horoscope(sign))
        if not alisa.get_user_state_object('sign'):
            alisa.suggest(self.one_of(['Запомнить знак']), 'save_user_sign', payload={'sign': sign.value})
        alisa.suggest(self.one_of(['Другой знак']), 'request_sign', payload={'reset_sign': True})

    def greetings(self, alisa: Alisa):
        alisa.tts_with_text(
            "Приветствую тебя в нейрогороскопе. Гороскопы сгенерированы нейросетью на текстах Сорокина и Пелевина. \n")
        self.request_sign(alisa)

    def request_sign(self, alisa: Alisa):
        alisa.tts_with_text("Для какого знака зодиака рассказать гороскоп?")
        alisa.voice_button(self.on_intent('SIGN'), 'tell_user_sign')
        alisa.update_user_state('sign', None)

    def tell_user_sign(self, alisa: Alisa):
        sign = Sign(alisa.get_intent_slot_value('SIGN', 'sign'))
        if sign:
            self.tell_horoscope_by_sign(alisa, sign)
        else:
            alisa.tts_with_text("Не распознала знак зодиака, попробуйте еще раз")
            alisa.voice_button(self.on_intent('SIGN'), 'tell_user_sign')

    def save_user_sign(self, alisa: Alisa):
        sign = alisa.get_button_payload_value('sign')
        alisa.tts_with_text(
            "Запомнила. Теперь каждый раз при входе в навык я буду говорить ваш гороскоп. "
            "Гороскопы обновляются раз в сутки.")
        alisa.update_user_state('sign', sign)
        alisa.end_session()

    def fallback(self, alisa):
        logging.info('FALLBACK: %r', alisa.get_original_utterance())
        alisa.tts_with_text(self.one_of([
            'Простите, я вас не поняла. ',
        ]))

        self.request_sign(alisa)

    def get_random_horoscope(self, sign: Sign):
        return horoscopes[sign].sample(n=1)['text'].iloc[0]

    def maybe(self, perc, value):
        if random.randint(0, 100) < perc:
            return value
        return ""


def read_horoscope(sign: Sign):
    return pd.read_csv('horoscopes/' + sign.value + '.csv')


horoscopes = {sign: read_horoscope(sign) for sign in Sign}
dialog = NeuroHoroscopeDialog()


@app.route("/", methods=['POST'])
def main():
    logging.info('Request: %r', request.json)

    response = {
        "version": request.json['version'],
        "response": {
            "end_session": False
        }
    }

    dialog.handle_dialog(Alisa(request, response))

    logging.info('Response: %r', response)

    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
