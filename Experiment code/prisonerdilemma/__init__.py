from mimetypes import init
from pickle import TRUE
from otree.api import *
import random
import time

from sqlalchemy import false

class C(BaseConstants):
    NAME_IN_URL='prisoner'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 1

    PAYOFFA = cu(1.2)
    PAYOFFB = cu(2.4)
    PAYOFFC = cu(3.6)
    PAYOFFD = cu(5.4)
    PAYOFFX = cu(0.25)

    PAYOFF_MATRIX = {
        (True, True): (PAYOFFC, PAYOFFC),
        (True, False): (PAYOFFA, PAYOFFD),
        (False, True): (PAYOFFD, PAYOFFA),
        (False, False): (PAYOFFB, PAYOFFB),
    }

    INSTRUCTIONS_TEMPLATE = __name__ + '/instructions.html'
    INSTRUCTIONS_FIRST_TEMPLATE = __name__ + '/instructions_first.html'
    INSTRUCTIONS_SECOND_TEMPLATE = __name__ + '/instructions_second.html'

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    first_player = models.IntegerField(initial=0)
    player_turn = models.IntegerField(initial=1)
    mode = models.IntegerField(initial=0)  # 0: baseline, 1: opaque, 2: transparent
    answer_state = models.BooleanField(initial=False)


class Player(BasePlayer):
    order_choice = models.StringField(initial='')
    choice = models.LongStringField(initial='')
    first_A_choice = models.CurrencyField(initial=0)
    first_B_choice = models.CurrencyField(initial=0)
    choice_done = models.BooleanField(initial=False)
    prolificID = models.StringField(initial='')
    elicit1 = models.IntegerField(
        blank=True,
        label="We would now like to ask you about how you think participants who choose second are likely to make their choice.\n"
            "We will randomly select 10 pairs of participants from today's experiment where the participant who chose first chose A.\n"
            "You will guess how many of the second participants chose A.\n"
            "If you are correct, you will earn a bonus payment of £0.25.\n"
            "Given that the first choice was A, how many of the 10 participants who chose second do you think chose A?\n",
        # choices=['0/10', '1/10', '2/10', '3/10', '4/10', '5/10', '6/10', '7/10', '8/10', '9/10', '10/10'],
        choices=[
            [0, '0/10'],
            [1, '1/10'],
            [2, '2/10'],
            [3, '3/10'],
            [4, '4/10'],
            [5, '5/10'],
            [6, '6/10'],
            [7, '7/10'],
            [8, '8/10'],
            [9, '9/10'],
            [10, '10/10'],
        ],
        widget=widgets.RadioSelectHorizontal
    )
    elicit2 = models.IntegerField(
        blank=True,
        label="We would now like to ask you about how you think participants who choose second are likely to make their choice.\n"
            "We will randomly select 10 pairs of participants from today's experiment where the participant who chose first chose B.\n"
            "You will guess how many of the second participants chose A.\n"
            "If you are correct, you will earn a bonus payment of £0.25.\n"
            "Given that the first choice was B, how many of the 10 participants who chose second do you think chose A?\n",
        # choices=['0/10', '1/10', '2/10', '3/10', '4/10', '5/10', '6/10', '7/10', '8/10', '9/10', '10/10'],
        choices=[
            [0, '0/10'],
            [1, '1/10'],
            [2, '2/10'],
            [3, '3/10'],
            [4, '4/10'],
            [5, '5/10'],
            [6, '6/10'],
            [7, '7/10'],
            [8, '8/10'],
            [9, '9/10'],
            [10, '10/10'],
        ],
        widget=widgets.RadioSelectHorizontal
    )
    pass

class Game(ExtraModel):
    group = models.Link(Group)
    choice1 = models.CurrencyField()
    choice2 = models.CurrencyField()
    payoff1 = models.CurrencyField()
    payoff2 = models.CurrencyField()
    
def getChoiceFromBool(choice):
    if choice:
        return 'A'
    return 'B'

def live_method(player, data):
    group = player.group
    my_id = player.id_in_group
    other_player = player.get_others_in_group()[0]

    if (player.prolificID == '' and player.participant.label is not None):
        player.prolificID = player.participant.label

    [game] = Game.filter(group = group)

    if data['type'] == 'choice':
        choice_field = 'choice{}'.format(my_id)
        other_choice_field = 'choice{}'.format(3 - my_id)
        # if my_id != group.player_turn:
        #     return
        # group.player_turn = 3 - group.player_turn

        if my_id == group.first_player:
            choice = data['choice']
            player.choice = player.participant.choice = getChoiceFromBool(choice)
            setattr(game, choice_field, choice)
            other_player.participant.other_choice = player.choice

            if player.choice == 'A' and other_player.choice_done:
                other_player.choice = other_player.participant.choice = player.participant.other_choice = getChoiceFromBool(player.first_A_choice)
                setattr(game, other_choice_field, player.first_A_choice)
            if player.choice == 'B' and other_player.choice_done:
                other_player.choice = other_player.participant.choice = player.participant.other_choice = getChoiceFromBool(player.first_B_choice)
                setattr(game, other_choice_field, player.first_B_choice)
        else:
            player.first_A_choice = data['A_choice']
            player.first_B_choice = data['B_choice']
            player.choice_done = True

            if other_player.choice == 'A':
                player.choice = player.participant.choice = other_player.participant.other_choice = getChoiceFromBool(player.first_A_choice)
                setattr(game, choice_field, player.first_A_choice)
            if other_player.choice == 'B':
                player.choice = player.participant.choice = other_player.participant.other_choice = getChoiceFromBool(player.first_B_choice)
                setattr(game, choice_field, player.first_B_choice)

        choices = (game.choice1, game.choice2)
        is_ready = None not in choices
        if is_ready:
            p1, p2 = group.get_players()
            [game.payoff1, game.payoff2] = C.PAYOFF_MATRIX[choices]
            p1.payoff = game.payoff1
            p2.payoff = game.payoff2
    if data['type'] == 'answer':
        group.answer_state = True
    return {
        1: dict (
            type = 'status',
            result = (1 == my_id and player.choice) or (1 != my_id and other_player.choice),
            finished = (1 == group.first_player and group.answer_state) or (1 != group.first_player and (player.choice_done or other_player.choice_done)),
            other_finished = (1 != group.first_player and group.answer_state) or (1 == group.first_player and (player.choice_done or other_player.choice_done))
        ),
        2: dict (
            type = 'status',
            result = (2 == my_id and player.choice) or (2 != my_id and other_player.choice),
            finished = (2 == group.first_player and group.answer_state) or (2 != group.first_player and (player.choice_done or other_player.choice_done)),
            other_finished = (2 != group.first_player and group.answer_state) or (2 == group.first_player and (player.choice_done or other_player.choice_done))
        ),
    }

def live_turn_method(player, data):
    session = player.session
    group = player.group
    my_id = player.id_in_group

    if session.config['mode'] == 0:
        group.first_player = 1
    if group.first_player > 0:
        return { 0: dict( type = 'finished' ) }
    if data['type'] == 'init':
        # if group.mode == -1:
        #     group.mode = random.choice([0, 1, 2])
        return { 0: dict( type='init', mode=session.config['mode'] ) }
    if data['type'] == 'turn':
        if (my_id != 1):
            return
        if data['turn'] == 1:
            player.order_choice = 'first'
        else:
            player.order_choice = 'second'
        group.first_player = data['turn']
        group.player_turn = group.first_player
    return { 0: dict( type = 'finished' ) }

class WaitToStart(WaitPage):
    # body_text = "Waiting for other participant. You will be paid for the waiting time."
    @staticmethod
    def after_all_players_arrive(group: Group):
        Game.create(group=group)

class Play(Page):
    form_model = 'player'
    form_fields = ['elicit1', 'elicit2']
    live_method = live_method

    @staticmethod
    def js_vars(player: Player):
        return dict(my_id = player.id_in_group, first_player = player.group.first_player, mode = player.session.config['mode'], fields=['elicit1', 'elicit2'])

class Instruct(Page):
    @staticmethod
    def vars_for_template(player):
        player.participant.start_time = time.time()
        return dict()
    pass

class Turn(Page):
    live_method = live_turn_method
    def js_vars(player: Player):
        return dict(my_id = player.id_in_group)

class Results(Page):
    pass

page_sequence = [WaitToStart, Instruct, Turn, Play]