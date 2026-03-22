from app.config import UPLOAD_FOLDER, OUTPUT_FOLDER
from flask import flash, redirect, url_for

def limit_dimensions(width, height):

    '''Scales down the image to MAX_DIMENSION if either width or height exceed MAX_DIMENSION.'''

    MAX_DIMENSION = 1080

    if width > MAX_DIMENSION:

        scaler = MAX_DIMENSION/width
        width = MAX_DIMENSION
        height *= scaler

    if height > MAX_DIMENSION:

        scaler = MAX_DIMENSION/height
        height = MAX_DIMENSION
        width *= scaler
    
    return width, height


def ensure_even_dimensions(width, height):

    '''Ensures both width and height are even'''

    if height % 2 == 1:
        print('Height is odd.')
        height -= 1
    else:
        print('Height is even')

    if width % 2 == 1:
        print('Width is odd.')
        width -= 1
    else:
        print('Width is even.')

    return width, height


def crop_video(source, crop_width, crop_height, crop_position_x, crop_position_y, fps):

    cropped_video = source.filter('crop', w=crop_width, h=crop_height, x=crop_position_x, y=crop_position_y)
    # .filter('fps', fps=fps, round='up')

    width = crop_width
    height = crop_height
    
    return cropped_video, width, height


def get_file_name(file_path):

    '''Generates output file name without the extensions'''
    
    from pathlib import Path

    file_path = Path(file_path)
    file_name = Path(file_path.parts[-1])

    file_extensions = "".join(file_name.suffixes)
    
    file_name = str(file_name).replace(file_extensions,'')

    return file_name


def generate(file_path, output_format, crop_width='iw', crop_height='ih', crop_position_x='(in_w-out_w)/2', crop_position_y='(in_h-out_h)/2', fps=25):

    import ffmpeg
    import logging

    logger = logging.getLogger(__name__)

    input_file = ffmpeg.input(file_path)

    success = True

    # Getting the dimensions of the file the user has submitted
    try:
        from . get_video_properties import get_video_properties
    except ImportError:
        from get_video_properties import get_video_properties

    video_properties = get_video_properties(file_path)

    width = int(video_properties['width'])
    height = int(video_properties['height'])

    # Placing a limit of the dimensions of this image
    width, height = limit_dimensions(width, height)
    width, height = ensure_even_dimensions(width, height)

    # Defining dimensions of the tile
    tile_width = width * 2
    tile_height = height * 2

    # This allows us to create four overlays from the same input
    split = input_file.split()

    # Apply a safe resize before compositing
    base = split[0].filter('scale', w=tile_width, h=tile_height, flags='lanczos')
    base = base.filter('format', 'yuv420p')

    # Applying transformation to the input file and creating the seamless output media
    canvas = base
    canvas = canvas.overlay(split[1].filter('scale', w=width, h=height).filter('format', 'yuv420p'), x=0, y=0)
    canvas = canvas.overlay(split[2].hflip().filter('scale', w=width, h=height).filter('format', 'yuv420p'), x=width, y=0)
    canvas = canvas.overlay(split[3].hflip().vflip().filter('scale', w=width, h=height).filter('format', 'yuv420p'), x=width, y=height)
    canvas = canvas.overlay(split[4].vflip().filter('scale', w=width, h=height).filter('format', 'yuv420p'), x=0, y=height)

    # Getting file name without extensions
    file_name = get_file_name(file_path)


    # File creation time
    from datetime import datetime
    creation_time = datetime.utcnow().strftime("%m%d%Y_%H%M%S")


    # Directory for generated files

    generated_file_directory = OUTPUT_FOLDER
    prefix = 'download_'

    import os
    output_file_path = os.path.join(generated_file_directory, prefix + creation_time)

    os.makedirs(output_file_path, exist_ok=True)

    # Defines output file name/path.
    output_location = f'{output_file_path}/seamlessly_{file_name}_{creation_time}.{output_format}'

    # Force a safe pixel format for output
    canvas = canvas.output(output_location, loop=0, pix_fmt='yuv420p')

    # --------------------------------------------------------------------------------------

    try:

        # Executes all of the above
        canvas.run(capture_stdout=True, capture_stderr=True)


    except ffmpeg._run.Error as e:
        logger.exception("FFmpeg produced an error")
        if getattr(e, "stderr", None):
            logger.error(e.stderr.decode("utf-8", errors="replace"))
        success = False


    finally:

        # REMOVING USER UPLOADED FILES

        from pathlib import Path
        import os

        print('DELETE:', file_path)

        # This deletes the file
        dirpath = Path(file_path)

        # This deletes the file subfolder IF there are no other files in it.
        try:
            folder_path = Path('/'.join(dirpath.parts[:-1]))
            print('FOLDER PATH:', folder_path) 
            if folder_path.exists() and folder_path.is_dir():
                os.rmdir(folder_path)
                print('Removed directory.')
        except OSError:
            print(f'{folder_path} cannot be deleted - folder is not empty yet.')

        # This deletes the entire directory IF there are no other files/folders in it.
        try:
            os.rmdir(UPLOAD_FOLDER)
        except OSError:
            print(f'{UPLOAD_FOLDER} cannot be deleted - folder is not empty yet.')


    return output_location, success
