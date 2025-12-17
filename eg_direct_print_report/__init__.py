from . import controller
from . import models


def _set_direct_print_post_init(env):
    env['ir.config_parameter'].sudo().set_param("eg_direct_print_report.all_print_preview", True)



