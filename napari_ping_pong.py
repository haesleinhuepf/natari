# GPU-accelerated (joking) Ping-Pong in napari
# --------------------------------------------
#
# Player 1 keys:
player1_up_key = 'w'
player1_down_key = 's'
#
# Player 2 keys:
player2_up_key = 'i'
player2_down_key = 'k'
#
# Have fun!
#   @haesleinhuepf

import pyclesperanto_prototype as cle

import time
import napari
from napari.qt.threading import thread_worker
from qtpy.QtWidgets import QLineEdit, QLabel, QWidget, QVBoxLayout

class Game:

    def __init__(self):
        """ Setup the game
        """
        self.player1_position = 200
        self.player2_position = 280

        self.player1_x = 10
        self.player2_x = 630

        self.player1_score = 0
        self.player2_score = 0

        self.width = 640
        self.height = 480
        self.playground = cle.create([self.height, self.width])

        self.bar_radius = 50

        self.puck_x = self.width / 2
        self.puck_y = self.height / 2
        self.puck_delta_x = 10
        self.puck_delta_y = 0

        self.result_label = QLabel()

    def game_step(self):
        """Forwards the game by one step and computes the new playground

        Returns
        -------
            an image with the current state of the game
        """

        # check player positions
        self.player1_position = self._check_player_position(self.player1_position)
        self.player2_position = self._check_player_position(self.player2_position)

        # move puck
        self.puck_x = self.puck_x + self.puck_delta_x
        self.puck_y = self.puck_y + self.puck_delta_y

        # check puck_position
        if self.puck_y < 0 or self.puck_y > self.height:
            self.puck_delta_y = -self.puck_delta_y
            self.puck_y = self.puck_y + self.puck_delta_y

        # puck at player 1
        if self.puck_x <= self.player1_x:
            self.puck_delta_x = -self.puck_delta_x
            self.puck_x = self.puck_x + self.puck_delta_x

            if abs(self.puck_y - self.player1_position) > self.bar_radius:
                # player 2 scores
                self.player2_score = self.player2_score + 1
                self._level_up()
            else:
                self.puck_delta_y = (self.puck_y - self.player1_position) / self.bar_radius * 5

        # puck at player 2
        if self.puck_x >= self.player2_x:
            self.puck_delta_x = -self.puck_delta_x
            self.puck_x = self.puck_x + self.puck_delta_x

            if abs(self.puck_y - self.player2_position) > self.bar_radius:
                # player 1 scores
                self.player1_score = self.player1_score + 1
                self._level_up()
            else:
                self.puck_delta_y = (self.puck_y - self.player2_position) / self.bar_radius * 5

        # show game status
        self.result_label.setText(str(self.player1_score) + ":" + str(self.player2_score))

        # draw playground
        cle.set(self.playground, 0.1)

        # draw player 1
        cle.draw_box(self.playground, self.player1_x, self.player1_position - self.bar_radius, 0, 3, self.bar_radius * 2, 0)

        # draw player 2
        cle.draw_box(self.playground, self.player2_x, self.player2_position - self.bar_radius, 0, 3, self.bar_radius * 2, 0)

        # draw puck
        cle.draw_sphere(self.playground, self.puck_x, self.puck_y, 0, 5, 3, 1)

        # return playground
        image = cle.pull_zyx(self.playground)

        return image

    def _check_player_position(self, position):
        """Checks if a player went out of the playground

        Parameters
        ----------
        position: int
            current position of the player

        Returns
        -------
            new, potentially corrected position of the player
        """

        if position - self.bar_radius < 0:
            position = self.bar_radius
        if position + self.bar_radius > self.height:
            position = self.height - self.bar_radius
        return position

    def _level_up(self):
        """If a player scores, the game restarts with smaller bars or accelerated puck speed.

        Returns
        -------

        """
        if self.bar_radius > 10:
            self.bar_radius = self.bar_radius - 10
        else:
            self.puck_delta_x = self.puck_delta_x / abs(self.puck_delta_x) * (abs(self.puck_delta_x) + 10)

        self.puck_x = self.width / 2
        self.puck_y = self.height / 2

# start up napari
with napari.gui_qt():
    viewer = napari.Viewer()

    game = Game()

    # Key bindings for user control
    @viewer.bind_key(player1_up_key)
    def player1_up_event(viewer):
        game.player1_position = game.player1_position - 10

    @viewer.bind_key(player1_down_key)
    def player1_down_event(viewer):
        game.player1_position = game.player1_position + 10

    @viewer.bind_key(player2_up_key)
    def player2_up_event(viewer):
        game.player2_position = game.player2_position - 10

    @viewer.bind_key(player2_down_key)
    def player2_down_event(viewer):
        game.player2_position = game.player2_position + 10

    # Graphical user interface
    widget = QWidget()
    layout = QVBoxLayout()
    widget.setLayout(layout)

    layout.addWidget(game.result_label)
    viewer.window.add_dock_widget(widget)
    game.result_label.setText(str("0:0"))

    # Multi-threaded interaction
    # inspired by https://napari.org/docs/dev/events/threading.html
    def update_layer(new_image):
        try:
            viewer.layers['result'].data = new_image
        except KeyError:
            viewer.add_image(
                new_image, name='result', contrast_limits=(0, 1)
            )

    @thread_worker
    def yield_random_images_forever():
        while True:  # infinite loop!
            yield game.game_step()
            time.sleep(0.05)

    # Start the game loop
    worker = yield_random_images_forever()
    worker.yielded.connect(update_layer)
    worker.start()
