# GPU-accelerated (joking) Ping-Pong in napari
# --------------------------------------------
#
# Player 1 keys:
player1_up_key = 'w'
player1_down_key = 's'
player1_front_key = 'a'
player1_back_key = 'd'
#
# Player 2 keys:
player2_up_key = 'i'
player2_down_key = 'k'
player2_front_key = 'j'
player2_back_key = 'l'
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
        self.width = 300
        self.height = 200
        self.depth = 200
        self.playground = cle.create([self.depth, self.height, self.width])
        self.gradient = cle.create([self.depth, self.height, self.width])
        cle.set_ramp_z(self.gradient)
        self.view = cle.create([self.depth, self.height, self.width])

        self.player1_y = self.height / 2
        self.player1_z = self.depth / 2
        self.player2_y = self.height / 2
        self.player2_z = self.depth / 2

        self.player1_x = 10
        self.player2_x = self.width - 10

        self.player1_score = 0
        self.player2_score = 0


        self.bar_radius = self.height / 4

        self.puck_x = self.width / 2
        self.puck_y = self.height / 2
        self.puck_z = self.depth / 2
        self.puck_delta_x = 10
        self.puck_delta_y = 0
        self.puck_delta_z = 0

        self.result_label = QLabel()

    def game_step(self):
        """Forwards the game by one step and computes the new playground

        Returns
        -------
            an image with the current state of the game
        """

        # check player positions
        self.player1_y, self.player1_z = self._check_player_position(self.player1_y,self.player1_z)
        self.player2_y, self.player2_z = self._check_player_position(self.player2_y,self.player2_z)

        # move puck
        self.puck_x = self.puck_x + self.puck_delta_x
        self.puck_y = self.puck_y + self.puck_delta_y
        self.puck_z = self.puck_z + self.puck_delta_z

        # check puck_position
        if self.puck_y < 0 or self.puck_y > self.height:
            self.puck_delta_y = -self.puck_delta_y
            self.puck_y = self.puck_y + self.puck_delta_y
        if self.puck_z < 0 or self.puck_z > self.depth:
            self.puck_delta_z = -self.puck_delta_z
            self.puck_z = self.puck_z + self.puck_delta_z

        # puck at player 1
        if self.puck_x <= self.player1_x:
            self.puck_delta_x = -self.puck_delta_x
            self.puck_x = self.puck_x + self.puck_delta_x

            if abs(self.puck_y - self.player1_y) > self.bar_radius or abs(self.puck_z - self.player1_z) > self.bar_radius:
                # player 2 scores
                self.player2_score = self.player2_score + 1
                self._level_up()
            else:
                self.puck_delta_y = (self.puck_y - self.player1_y) / self.bar_radius * 5
                self.puck_delta_z = (self.puck_z - self.player1_z) / self.bar_radius * 5

        # puck at player 2
        if self.puck_x >= self.player2_x:
            self.puck_delta_x = -self.puck_delta_x
            self.puck_x = self.puck_x + self.puck_delta_x

            if abs(self.puck_y - self.player2_y) > self.bar_radius or abs(self.puck_z - self.player2_z) > self.bar_radius :
                # player 1 scores
                self.player1_score = self.player1_score + 1
                self._level_up()
            else:
                self.puck_delta_y = (self.puck_y - self.player2_y) / self.bar_radius * 5
                self.puck_delta_z = (self.puck_z - self.player2_z) / self.bar_radius * 5

        # show game status
        self.result_label.setText(str(self.player1_score) + ":" + str(self.player2_score))

        # draw playground
        cle.set(self.playground, 0.0)

        # draw player 1
        cle.draw_box(self.playground, self.player1_x, self.player1_y - self.bar_radius, self.player1_z - self.bar_radius, 3, self.bar_radius * 2, self.bar_radius * 2)

        # draw player 2
        cle.draw_box(self.playground, self.player2_x, self.player2_y - self.bar_radius, self.player2_z - self.bar_radius, 3, self.bar_radius * 2, self.bar_radius * 2)

        # draw puck
        cle.draw_sphere(self.playground, self.puck_x, self.puck_y, self.puck_z, 5, 3, 3, 1)

        # put z-color coding on playground
        cle.multiply_images(self.playground, self.gradient, self.view)

        # return playground
        image = cle.pull_zyx(self.view)

        return image

    def _check_player_position(self, y, z):
        """Checks if a player went out of the playground

        Parameters
        ----------
        y: int
            current position of the player

        Returns
        -------
            new, potentially corrected position of the player
        """

        if y - self.bar_radius < 0:
            y = self.bar_radius
        if y + self.bar_radius > self.height:
            y = self.height - self.bar_radius

        if z - self.bar_radius < 0:
            z = self.bar_radius
        if z + self.bar_radius > self.depth:
            z = self.depth - self.bar_radius

        return y, z

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
        self.puck_z = self.depth / 2

# start up napari
with napari.gui_qt():
    viewer = napari.Viewer()

    game = Game()

    step = 10

    # Key bindings for user control
    @viewer.bind_key(player1_up_key)
    def player1_up_event(viewer):
        game.player1_y = game.player1_y - step

    @viewer.bind_key(player1_down_key)
    def player1_down_event(viewer):
        game.player1_y = game.player1_y + step

    @viewer.bind_key(player1_front_key)
    def player1_up_event(viewer):
        game.player1_z = game.player1_z - step

    @viewer.bind_key(player1_back_key)
    def player1_down_event(viewer):
        game.player1_z = game.player1_z + step

    @viewer.bind_key(player2_up_key)
    def player2_up_event(viewer):
        game.player2_y = game.player2_y - step

    @viewer.bind_key(player2_down_key)
    def player2_down_event(viewer):
        game.player2_y = game.player2_y + step

    @viewer.bind_key(player2_front_key)
    def player2_up_event(viewer):
        game.player2_z = game.player2_z - step

    @viewer.bind_key(player2_back_key)
    def player2_down_event(viewer):
        game.player2_z = game.player2_z + step


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
                new_image, name='result', contrast_limits=(0, game.depth)
            )

    @thread_worker
    def yield_random_images_forever():
        while True:  # infinite loop!
            yield game.game_step()
            time.sleep(0.1)

    # Start the game loop
    worker = yield_random_images_forever()
    worker.yielded.connect(update_layer)
    worker.start()
