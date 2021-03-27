# GPU-accelerated Ping-Pong in napari with hands-on experience
# ------------------------------------------------------------
#
# In order to make this script run, you need to install
# pyopencl, pyclesperanto-prototype==0.7.4, opencv-python and napari
#
# Have fun!
#   @haesleinhuepf

import pyclesperanto_prototype as cle

import time
import napari
from napari.qt.threading import thread_worker
from qtpy.QtWidgets import QLabel, QWidget, QVBoxLayout
from qtpy.QtWidgets import QAction

import cv2
import numpy as np

class Game:

    def __init__(self):
        self._video_source = None
        self.reset()

    def reset(self):
        """ Setup the game
        """
        self.player1_position = 200
        self.player2_position = 280

        self.player1_x = 10
        self.player2_x = 630

        self.player1_score = 0
        self.player2_score = 0


        # Start webcam
        if self._video_source is None:
            self._video_source = cv2.VideoCapture(0)

        # read augmentable playground
        _, picture = self._video_source.read()
        self._image_at_beginning = self._push_and_format(picture)

        # setup virtual playground
        self.width = self._image_at_beginning.shape[2]
        self.height = self._image_at_beginning.shape[1]

        self.playground = cle.create([self.height, self.width])

        # configure toys
        self.bar_radius = 75

        self.puck_x = self.width / 2
        self.puck_y = self.height / 2
        self.puck_delta_x = 10
        self.puck_delta_y = 0

        self.puck_width = 50
        self.puck_height = 40

        self.sensitive_area_width = 100

        # setup GUI
        self.result_label = QLabel()



    def game_step(self):
        """Forwards the game by one step and computes the new playground

        Returns
        -------
            an image with the current state of the game
        """

        # read camera image
        _, picture = self._video_source.read()

        # push to GPU and bring in right format
        current_image = self._push_and_format(picture)

        # determine
        difference = cle.sum_z_projection(cle.squared_difference(current_image, self._image_at_beginning))
        crop_left = cle.crop(difference, start_x=0, start_y=0, width=self.sensitive_area_width, height=self.height)
        crop_right = cle.crop(difference, start_x=self.width - self.sensitive_area_width, start_y=0, width=self.sensitive_area_width, height=self.height)

        # check player positions
        self.player1_position = self._determine_player_position(self.player1_position, crop_left)
        self.player2_position = self._determine_player_position(self.player2_position, crop_right)
        squared_difference_picture = cle.pull(difference)

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
        cle.draw_sphere(self.playground, self.puck_x - self.puck_width / 2, self.puck_y - self.puck_height / 2, 0, self.puck_width, self.puck_height, 1)

        # binary playground image
        game_state = cle.pull(self.playground)

        # turn camera view in single channel grey-value image
        grey = cle.mean_z_projection(current_image)

        # warp the image
        gradient_radius = 25
        position_delta = 25000
        blurred_playground = cle.gaussian_blur(self.playground, sigma_x=gradient_radius, sigma_y=gradient_radius)
        gradient = cle.laplace_box(blurred_playground)
        vector_x = cle.multiply_image_and_scalar(gradient, scalar=position_delta)
        vector_y = cle.multiply_image_and_scalar(gradient, scalar=position_delta)
        warped_playground = cle.apply_vector_field(grey, vector_x, vector_y)

        return [
                    # images to add in napari
                    [cle.pull(grey), squared_difference_picture, game_state, cle.pull(vector_x), cle.pull(vector_x), cle.pull(warped_playground)],
                    # names
                    ['camera input', 'squared difference',      'game state', 'vector x',        'vector y',         'warped view' ],
                    # visibility
                    [False,          False,                      False,      False,              False,              True]
                ]

    def _push_and_format(self, picture):
        """
        Pushs a given camera picture to GPU memory and brings it in the right shape/dimension

        Parameters
        ----------
        picture : numpy array
            camera picture

        Returns
        -------
        cle.Image

        """
        result = cle.flip(cle.transpose_xy(cle.transpose_xz(cle.push(picture))), flip_x=True, flip_y=False, flip_z=False)
        return result

    def _determine_player_position(self, former_position, image):
        new_position = cle.center_of_mass(cle.multiply_images(image, image))[1]
        return new_position

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

    # Add a menu
    action = QAction('Restart Ping Pong', viewer.window._qt_window)
    action.triggered.connect(game.reset)
    viewer.window.plugins_menu.addAction(action)

    # Graphical user interface
    widget = QWidget()
    layout = QVBoxLayout()
    widget.setLayout(layout)

    layout.addWidget(game.result_label)
    viewer.window.add_dock_widget(widget)
    game.result_label.setText(str("0:0"))

    # Multi-threaded interaction
    # inspired by https://napari.org/docs/dev/events/threading.html
    def update_layer(data):

        new_images, names, visiblity = data

        for i, new_image in enumerate(new_images):
            if new_image is not None:
                try:
                    viewer.layers[names[i]].data = new_image
                except KeyError:
                    viewer.add_image(
                        new_image, name=names[i], blending='additive', visible=visiblity[i]
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
