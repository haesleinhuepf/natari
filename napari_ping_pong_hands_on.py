# GPU-accelerated (joking) Ping-Pong in napari
# --------------------------------------------
#
# Have fun!
#   @haesleinhuepf

import pyclesperanto_prototype as cle

import time
import napari
from napari.qt.threading import thread_worker
from qtpy.QtWidgets import QLineEdit, QLabel, QWidget, QVBoxLayout

import cv2
import numpy as np

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


        # Start webcam
        self.video_source = cv2.VideoCapture(0)
        _, self.former_picture = self.video_source.read()
        self.width = self.former_picture.shape[1]
        self.height = self.former_picture.shape[0]

        self.playground = cle.create([self.height, self.width])

        self.bar_radius = 75

        self.puck_x = self.width / 2
        self.puck_y = self.height / 2
        self.puck_delta_x = 10
        self.puck_delta_y = 0

        self.sensitive_area_width = 100

        self.result_label = QLabel()



    def game_step(self):
        """Forwards the game by one step and computes the new playground

        Returns
        -------
            an image with the current state of the game
        """

        # check player positions
        _, picture = self.video_source.read()
        image1 = cle.flip(cle.push(np.transpose(picture, (2, 0, 1))), flip_x=True, flip_y=False, flip_z=False)
        image2 = cle.flip(cle.push(np.transpose(self.former_picture, (2, 0, 1))), flip_x=True, flip_y=False, flip_z=False)
        difference = cle.sum_z_projection(cle.squared_difference(image1, image2))
        crop_left = cle.crop(difference, start_x=0, start_y=0, width=self.sensitive_area_width, height=self.height)
        crop_right = cle.crop(difference, start_x=self.width - self.sensitive_area_width, start_y=0, width=self.sensitive_area_width, height=self.height)

        self.player1_position = self._determine_player_position(self.player1_position, crop_left) #self._check_player_position(self.player1_position)
        self.player2_position = self._determine_player_position(self.player2_position, crop_right) #self._check_player_position(self.player2_position)
        difference_picture = cle.pull(difference)

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
        game_state = cle.pull(self.playground)

        return [difference_picture, np.flip(picture, axis=1), game_state]

    def _determine_player_position(self, former_position, image):
        new_position = cle.center_of_mass(cle.multiply_images(image, image))[1]
        intensity = cle.maximum_of_all_pixels(image)
        return new_position

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

    # Graphical user interface
    widget = QWidget()
    layout = QVBoxLayout()
    widget.setLayout(layout)

    layout.addWidget(game.result_label)
    viewer.window.add_dock_widget(widget)
    game.result_label.setText(str("0:0"))

    # Multi-threaded interaction
    # inspired by https://napari.org/docs/dev/events/threading.html
    def update_layer(new_images):
        for i, new_image in enumerate(new_images):
            if new_image is not None:
                try:
                    viewer.layers['result' + str(i)].data = new_image
                except KeyError:
                    viewer.add_image(
                        new_image, name='result' + str(i), blending='additive'
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
