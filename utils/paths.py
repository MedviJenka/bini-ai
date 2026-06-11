from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT_DIR / "tests" / "data"

IMAGE_DIR = ROOT_DIR / "tests" / "data" / "images"


# --------------------------------------------- #
#      Images paths retrieved from data dir     #
# --------------------------------------------- #

class ImagePaths:
    MAIN_IMAGE                  = str(IMAGE_DIR / "main.png")
    SAMPLE_IMAGE                = str(IMAGE_DIR / "image01.png")
    CAT_IMAGE                   = str(IMAGE_DIR / "cat.jpg")
    IR_IMAGE                    = str(IMAGE_DIR / "ir_list_view.png")
    IR_PLAY_BUTTON_SAMPLE_IMAGE = str(IMAGE_DIR / "ir_play_button_sample_image.png")
    WELCOME_IMAGE               = str(IMAGE_DIR / 'welcome.png')
    VOLUME_ICON_SAMPLE_IMAGE    = str(IMAGE_DIR / "volume_icon.png")
    TAG_ICON_SAMPLE_IMAGE       = str(IMAGE_DIR / 'tag_sample.png')
    PAUSE_RESUME_MAIN_IMAGE     = str(IMAGE_DIR / 'pause_resume_main.png')
    PAUSE_RESUME_SAMPLE_IMAGE   = str(IMAGE_DIR / 'pause_resume_sample.png')
    IR_PLAYER                   = str(IMAGE_DIR / 'ir_player.png')
    IDENTICAL_IMAGE_1           = str(IMAGE_DIR / 'identical_image_1.png')
    IDENTICAL_IMAGE_2           = str(IMAGE_DIR / 'identical_image_2.png')
    GOOGLE_MAIN_PAGE            = str(IMAGE_DIR / 'google_main_page.png')
    LEGAL_HOLD                  = str(IMAGE_DIR / 'legal_hold.png')
    IR_METADATA                 = str(IMAGE_DIR / 'ir_metadata.png')
    VOCA                        = str(IMAGE_DIR / 'voca.png')
    VOCA_SAMPLE_IMAGE           = str(IMAGE_DIR / 'voca_sample_image.png')


class AudioPaths:
    ENGLISH_30_SEC = str(DATA_DIR / 'english_30_sec.mp3')
