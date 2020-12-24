# Snake in napari
# ---------------
#
# Player 1 keys:
player1_up_key = 'w'
player1_down_key = 's'
player1_left_key = 'a'
player1_right_key = 'd'

# Player 1 keys:
player2_up_key = 'i'
player2_down_key = 'k'
player2_left_key = 'j'
player2_right_key = 'l'

#
# Have fun!
#   @haesleinhuepf

import pyclesperanto_prototype as cle

import time
import napari
import numpy as np
from napari.qt.threading import thread_worker
from qtpy.QtWidgets import QLineEdit, QLabel, QWidget, QVBoxLayout

class Game:

    def __init__(self):
        """ Setup the game
        """

        # playground config
        self.width = 640
        self.height = 480

        self.pixel_size = 10
        self.food_calories = 5
        self.maximum_food_available = 10

        self.frame_delay = 0.2 # seconds

        # player 1
        self.player1_delta_x = 0
        self.player1_delta_y = self.pixel_size
        self.player1_score = 0
        self.player1_positions = [
            [240, 240]
        ]

        # player 2
        self.player2_delta_x = 0
        self.player2_delta_y = -self.pixel_size
        self.player2_score = 0
        self.player2_positions = [
            [480, 240]
        ]

        self.food_positions = []

        # others
        self.iteration = 0

        self.playground = cle.create([self.height, self.width])
        self.temp = cle.create([self.height, self.width])

        self.result_label = QLabel()

    def set_player1_direction(self, delta_x, delta_y):
        self.player1_delta_x = delta_x * self.pixel_size
        self.player1_delta_y = delta_y * self.pixel_size

    def set_player2_direction(self, delta_x, delta_y):
        self.player2_delta_x = delta_x * self.pixel_size
        self.player2_delta_y = delta_y * self.pixel_size

    def game_step(self):
        """Forwards the game by one step and computes the new playground

        Returns
        -------
            an image with the current state of the game
        """

        self.result_label.setText(str(self.player1_score) + " : " + str(self.player2_score))

        # move player 1
        result = self.move_player(self.player1_positions, self.player1_delta_x, self.player1_delta_y, self.player1_score)
        if result is None:
            return cle.pull_zyx(self.playground)
        self.player1_positions = result

        # move player 2
        result = self.move_player(self.player2_positions, self.player2_delta_x, self.player2_delta_y, self.player2_score)
        if result is None:
            return cle.pull_zyx(self.playground)
        self.player2_positions = result

        # go through food positions and check if a player ate it
        new_food_positions = []
        for pos in self.food_positions:
            if pos == self.player1_positions[0]:
                self.player1_score = self.player1_score + self.food_calories
            elif pos == self.player2_positions[0]:
                self.player2_score = self.player2_score + self.food_calories
            else:
                new_food_positions.append(pos)
        self.food_positions = new_food_positions

        # seed new food from time to time
        if len(self.food_positions) < self.maximum_food_available:
            random_x = (int(np.random.random_sample() * self.width / self.pixel_size - 2) + 1) * self.pixel_size
            random_y = (int(np.random.random_sample() * self.height / self.pixel_size - 2) + 1) * self.pixel_size
            if [random_x, random_y] not in self.player1_positions and \
                [random_x, random_y] not in self.player2_positions and \
                [random_x, random_y] not in self.food_positions:
                self.food_positions.append([random_x, random_y])

        # draw playground frame
        cle.draw_box(self.temp, 0, 0, 0, self.width, self.height, 1, 4)
        cle.draw_box(self.temp, 1, 1, 0, self.width - 3, self.height - 3, 1, 0)

        # draw players and food
        self.draw_positions(self.player1_positions, 2)
        self.draw_positions(self.player2_positions, 7)
        self.draw_positions(self.food_positions, 10)

        cle.maximum_sphere(self.temp, self.playground, self.pixel_size / 2, self.pixel_size / 2)

        # return playground
        image = cle.pull_zyx(self.playground)

        return image

    def move_player(self, positions, player_delta_x, player_delta_y, player_score):
        """ Move a player by one step and check if it hit the wall, itself or the other player.
        The game is over then.
        """
        player_position_x = positions[0][0] + player_delta_y
        player_position_y = positions[0][1] + player_delta_x

        if self.is_game_over(player_position_x, player_position_y):
            print("Player 1: Game over!")
            time.sleep(5)
            self.__init__()
            return None

        # move snake ahead
        new_positions = [
            [player_position_x, player_position_y]
        ]
        for i, pos in enumerate(positions):
            if i > player_score + 2:
                break
            new_positions.append(pos)


        return new_positions

    def is_game_over(self, player_position_x, player_position_y):
        return [player_position_x, player_position_y] in self.player1_positions or \
               [player_position_x, player_position_y] in self.player2_positions or \
               player_position_x <= 0 or \
               player_position_x >= self.width or \
               player_position_y <= 0 or \
               player_position_y >= self.height

    def draw_positions(self, new_positions, value):
        """bring position lists in the right format and draw the list of coordinates in a given color on the playground.
        """
        positions = cle.push(np.asarray(new_positions))
        values_and_positions = cle.create([positions.shape[0] + 1, positions.shape[1]])
        cle.set(values_and_positions, value)
        cle.paste(positions, values_and_positions, 0, 0)
        cle.write_values_to_positions(values_and_positions, self.temp)

# start up napari
with napari.gui_qt():
    viewer = napari.Viewer(title="natari")

    game = Game()

    # Key bindings for user control
    @viewer.bind_key(player1_up_key)
    def player1_up_event(viewer):
        game.set_player1_direction(-1, 0)

    @viewer.bind_key(player1_down_key)
    def player1_down_event(viewer):
        game.set_player1_direction(1, 0)

    @viewer.bind_key(player1_left_key)
    def player1_left_event(viewer):
        game.set_player1_direction(0, -1)

    @viewer.bind_key(player1_right_key)
    def player1_right_event(viewer):
        game.set_player1_direction(0, 1)

    # Key bindings for user control
    @viewer.bind_key(player2_up_key)
    def player2_up_event(viewer):
        game.set_player2_direction(-1, 0)

    @viewer.bind_key(player2_down_key)
    def player2_down_event(viewer):
        game.set_player2_direction(1, 0)

    @viewer.bind_key(player2_left_key)
    def player2_left_event(viewer):
        game.set_player2_direction(0, -1)

    @viewer.bind_key(player2_right_key)
    def player2_right_event(viewer):
        game.set_player2_direction(0, 1)

    # Graphical user interface
    widget = QWidget()
    layout = QVBoxLayout()
    widget.setLayout(layout)

    layout.addWidget(game.result_label)
    viewer.window.add_dock_widget(widget)
    game.result_label.setText(str("0"))

    # Multi-threaded interaction
    # inspired by https://napari.org/docs/dev/events/threading.html
    def update_layer(new_image):
        try:
            viewer.layers['result'].data = new_image
        except KeyError:
            viewer.add_image(
                new_image, name='result', contrast_limits=(0, 10), colormap='turbo'
            )

    @thread_worker
    def yield_random_images_forever():
        while True:  # infinite loop!
            yield game.game_step()
            time.sleep(game.frame_delay)

    # Start the game loop
    worker = yield_random_images_forever()
    worker.yielded.connect(update_layer)
    worker.start()
