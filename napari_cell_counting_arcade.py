# Cell Counting Arcade
#
# This game runs in napari, shows an image with nuclei and cells.
# It uses numpy and clesperanto to draw a playground where you
# can remove cells by shooting at them.
#
# Have fun!
#   @haesleinhuepf
#
# Installation: It's recommended to install these dependencies
# before running the game from the command line:
#
# conda install -c conda-forge pyopencl
# pip install pyclesperanto-prototype
# pip install napari==0.4.8
# pip install jupyter
#
# Player keys:
player_left_key = "1"
player_right_key = "2"
player_fire_key = "9"
#
#
# We used image set BBBC022v1 [Gustafsdottir et al., PLOS ONE, 2013], available from the
# Broad Bioimage Benchmark Collection [Ljosa et al., Nature Methods, 2012].
from skimage.io import imread
dataset = imread("data/IXMtest_A02_s9.tif")
nuclei_channel = 0
colours = ['magenta', 'green', 'cyan']

import time
import napari
from napari._qt.qthreading import thread_worker
from napari.types import LabelsData
import pyclesperanto_prototype as cle
import numpy as np

# Open a napari viewer
viewer = napari.Viewer()

# add the original image channels as independent layers
for i in range(0, dataset.shape[2]):
    viewer.add_image(dataset[:,:,i], blending='additive', colormap=colours[i], name='channel' + str(i + 1))

# image segmentation: nuclei and cells
binary_image = cle.threshold_otsu(dataset[:,:, nuclei_channel])
labels_nuclei = cle.connected_components_labeling_box(binary_image)
labels_cells = cle.extend_labels_with_maximum_radius(labels_nuclei, radius=30)

# The game
class CellCountingArcade():
    """
    The game allows the player to shoot bullets from the bottom of the screen which move up and if they hit a nucleus
    it is removed from the image data in the viewer with the surrounding cell.
    """
    def __init__(self, nuclei : LabelsData, cells : LabelsData, viewer : napari.Viewer):
        self.nuclei = nuclei
        self.cells = cells
        self.viewer = viewer
        self.player_position = nuclei.shape[1] / 2
        self.bullets = []
        self.playground = cle.create_labels_like(nuclei)

    def move_player(self, delta):
        """
        Move the player left/right.
        """
        if self.player_position + delta > 0 and self.player_position + delta < self.nuclei.shape[1]:
            self.player_position += delta

    def fire(self):
        """
        Shoot a bullet
        """
        self.bullets.append([self.player_position, 0])

    def game_loop(self):
        """
        This function is called at every game iteration. It checks if bullets hit nuclei and redraws the playground
        """
        bullet_radius = 5

        # empty playground
        cle.set(self.playground, 0)

        # pull nuclei from GPU so that we can access individual pixels
        nuclei = np.asarray(self.nuclei)
        # prepare all existing labels in a list. We set them to 0 in case a nucleus was hit
        labels_to_keep = list(range(0, int(np.max(self.nuclei)+1)))

        # future bullets to keep
        new_bullets = []

        for bullet in self.bullets:
            bullet[1] += 10

            # check if a bullet has hit a nucleus
            try:
                label = nuclei[int(self.playground.shape[0] - bullet[1]), int(bullet[0])]
            except IndexError:
                label = 0
            if label != 0: # bullet has hit a nucleus
                labels_to_keep[label] = 0
            elif bullet[1] > self.playground.shape[1]:
                pass # bullet has left the playground
            else:
                new_bullets.append(bullet)
                # draw bullets
                cle.draw_sphere(self.playground, bullet[0], self.playground.shape[0] - bullet[1], 0, bullet_radius, bullet_radius, 1, 1)
        self.bullets = new_bullets

        # only keep cells where the nuclei weren't hit
        new_label_ids = np.asarray(labels_to_keep)
        cle.replace_intensities(self.nuclei, new_label_ids, self.nuclei)
        cle.replace_intensities(self.cells, new_label_ids, self.cells)

        # make a binary image of areas to keep
        binary = self.cells > 0

        # draw player
        cle.draw_box(self.playground, self.player_position - 5, self.playground.shape[0] - 20, 0, 10, 20, 1, 2)
        cle.draw_box(self.playground, self.player_position - 15, self.playground.shape[0] - 10, 0, 30, 10, 1, 2)

        # collect all layers in a dictionary
        result = {}
        for layer in self.viewer.layers:
            result[layer.name] = cle.multiply_images(layer.data, binary)

        # add segmentation (inivisble) and playground
        result['nuclei'] = self.nuclei
        result['cells'] = self.cells
        result['playground'] = cle.copy(self.playground)

        return result



def update_layers(images_data: dict):
    """
    Add images to napari is layer or updates a pre-existing layer
    """
    for name in images_data.keys():
        image = images_data[name]
        for layer in viewer.layers:
            if layer.name == name:
                layer.data = image
                image = None
                break

        if image is not None:
            if "nuclei" in name or "cells" in name: # or "playground" in name:
                viewer.add_labels(image, name=name, visible="playground" in name)
            else:
                viewer.add_image(image, name=name, blending='additive')


game = CellCountingArcade(labels_nuclei, labels_cells, viewer)

# Key bindings for the game
@viewer.bind_key(player_left_key)
def player_left_event(viewer):
    game.move_player(-10)

@viewer.bind_key(player_right_key)
def player_right_event(viewer):
    game.move_player(10)

@viewer.bind_key(player_fire_key)
def player_left_event(viewer):
    game.fire()

# Game loop, runs in the background
# https://napari.org/guides/stable/threading.html
@thread_worker
def loop_run():
    while True: # endless loop
        data = game.game_loop()
        yield data
        time.sleep(0.1)

# Start the loop
worker = loop_run()
worker.yielded.connect(update_layers)
worker.start()

napari.run()



