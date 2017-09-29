import datetime
import os
import tempfile
import StringIO
import zipfile

import subprocess
from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from geonode.layers.views import _resolve_layer, _PERMISSION_MSG_VIEW


def clip_layer(request, layername):
    """Clipping raster layer and save to temp folder.
    Clipping layer by bbox or by geojson.
    :param layername: The layer name in Geonode.
    :type layername: basestring
    :return: file size
    """
    # PREPARATION
    layer = _resolve_layer(
        request,
        layername,
        'base.view_resourcebase',
        _PERMISSION_MSG_VIEW)

    query = request.GET or request.POST
    params = {
        param.upper(): value for param, value in query.iteritems()}
    bbox_string = params.get('BBOX', '')
    geojson = params.get('GEOJSON', '')
    current_date = datetime.datetime.today().strftime('%Y-%m-%d_%H-%M-%S')

    # create temp folder
    temporary_folder = os.path.join(
        tempfile.gettempdir(), 'clipped')
    try:
        os.mkdir(temporary_folder)
    except OSError as e:
        pass

    # get file for raster
    raster_filepath = None
    extention = ''

    file_names = []
    for layerfile in layer.upload_session.layerfile_set.all():
        file_names.append(layerfile.file.path)

    for target_file in file_names:
        if '.tif' in target_file:
            raster_filepath = target_file
            extention = 'tif'
            break

    # get temp filename for output
    filename = os.path.basename(raster_filepath)
    clip_filename = filename + '.' + current_date + '.' + extention

    if bbox_string:
        output = os.path.join(
            temporary_folder,
            clip_filename
        )
        clipping = (
            'gdal_translate -projwin ' +
            '%(CLIP)s %(PROJECT)s %(OUTPUT)s'
        )
        request_process = clipping % {
            'CLIP': bbox_string.replace(',', ' '),
            'PROJECT': raster_filepath,
            'OUTPUT': output,
        }
    elif geojson:
        output = os.path.join(
            temporary_folder,
            clip_filename
        )
        mask_file = os.path.join(
            temporary_folder,
            filename + '.' + current_date + '.geojson'
        )
        _file = open(mask_file, 'w+')
        _file.write(geojson)
        _file.close()

        masking = ('gdalwarp -dstnodata 0 -q -cutline %(MASK)s ' +
                   '-crop_to_cutline ' +
                   '-dstalpha -of ' +
                   'GTiff %(PROJECT)s %(OUTPUT)s')
        request_process = masking % {
            'MASK': mask_file,
            'PROJECT': raster_filepath,
            'OUTPUT': output,
        }
    else:
        raise Http404('No bbox or geojson in parameters.')

    # generate if output is not created
    if not os.path.exists(output):
        if raster_filepath:
            subprocess.call(request_process, shell=True)

    if os.path.exists(output):
        # Check size
        max_clip_size = settings.MAXIMUM_CLIP_SIZE
        clipped_size = os.path.getsize(output)

        if float(clipped_size) > float(max_clip_size):
            response = JsonResponse({
                'error': 'Clipped file size is '
                         'bigger than ' + max_clip_size + ' bytes'
            })
            response.status_code = 403
            return response

        response = JsonResponse({
            'success': 'Successfully clipping layer',
            'clip_filename': clip_filename
        })
        response.status_code = 200
        return response
    else:
        raise Http404('Project can not be clipped or masked.')


def download_clip(request, layername, clip_filename):
    """Download clipped file.
    Clipping layer by bbox or by geojson.
    :param layername: The layer name in Geonode.
    :type layername: basestring
    :param clip_filename: clipped filename
    :type clip_filename: basestring
    :return: The HTTPResponse with a file.
    """
    # PREPARATION
    layer = _resolve_layer(
        request,
        layername,
        'base.view_resourcebase',
        _PERMISSION_MSG_VIEW)

    query = request.GET or request.POST
    params = {
        param.upper(): value for param, value in query.iteritems()}
    current_date = datetime.datetime.today().strftime('%Y-%m-%d_%H-%M-%S')

    # create temp folder
    temporary_folder = os.path.join(
        tempfile.gettempdir(), 'clipped')
    try:
        os.mkdir(temporary_folder)
    except OSError as e:
        pass

    # get file for raster
    raster_filepath = None
    extention = ''

    file_names = []
    for layerfile in layer.upload_session.layerfile_set.all():
        file_names.append(layerfile.file.path)

    for target_file in file_names:
        if '.tif' in target_file:
            raster_filepath = target_file
            extention = 'tif'
            break

    # get temp filename for output
    filename = os.path.basename(raster_filepath)

    output = os.path.join(
        temporary_folder,
        clip_filename
    )

    if os.path.exists(output):
        # Create zip file
        s = StringIO.StringIO()
        zf = zipfile.ZipFile(s, "w")

        zip_subdir = layer.name + '_clipped'
        zip_filename = "%s.zip" % zip_subdir

        files_to_zipped = []
        for filename in file_names:
            if not filename.endswith('.qgs') and \
                    not filename.endswith(extention):
                files_to_zipped.append(filename)

        for fpath in files_to_zipped:
            # Calculate path for file in zip
            fdir, fname = os.path.split(fpath)
            fnames = fname.split('.')
            fname = fnames[0] + '.' + current_date + '.' + fnames[1]
            zip_path = os.path.join(zip_subdir, fname)
            zf.write(fpath, zip_path)

        # Add clipped raster
        opath, oname = os.path.split(output)
        zip_path = os.path.join(zip_subdir, oname)
        zf.write(output, zip_path)

        # Must close zip for all contents to be written
        zf.close()
        resp = HttpResponse(
            s.getvalue(), content_type="application/x-zip-compressed")
        resp['Content-Disposition'] = 'attachment; filename=%s' % zip_filename
        return resp
    else:
        raise Http404('Project can not be clipped or masked.')