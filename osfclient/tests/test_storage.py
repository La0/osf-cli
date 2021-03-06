from unittest.mock import patch, MagicMock, call

import pytest

from osfclient.models import OSFCore
from osfclient.models import Storage
from osfclient.models import File
from osfclient.models import Folder

from osfclient.tests import fake_responses
from osfclient.tests.mocks import FakeResponse


@patch.object(OSFCore, '_get')
def test_iterate_files(OSFCore_get):
    store = Storage({})
    store._files_url = 'https://api.osf.io/v2//nodes/f3szh/files/osfstorage'

    json = fake_responses.files_node('f3szh', 'osfstorage',
                                     ['hello.txt', 'bye.txt'])
    response = FakeResponse(200, json)
    OSFCore_get.return_value = response

    files = list(store.files)

    assert len(files) == 2
    for file_ in files:
        assert isinstance(file_, File)
        assert file_.session == store.session

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2//nodes/f3szh/files/osfstorage')


@patch.object(OSFCore, '_get')
def test_iterate_folders(OSFCore_get):
    store = Storage({})
    store._files_url = 'https://api.osf.io/v2//nodes/f3szh/files/osfstorage'

    json = fake_responses.files_node('f3szh', 'osfstorage',
                                     folder_names=['foo', 'bar'])
    response = FakeResponse(200, json)
    OSFCore_get.return_value = response

    folders = list(store.folders)

    assert len(folders) == 2
    for folder in folders:
        assert isinstance(folder, Folder)
        assert folder.session == store.session
        assert folder.name in ('foo', 'bar')

    OSFCore_get.assert_called_once_with(
        'https://api.osf.io/v2//nodes/f3szh/files/osfstorage')


def test_iterate_files_and_folders():
    # check we attempt to recurse into the folders
    store = Storage({})
    store._files_url = 'https://api.osf.io/v2//nodes/f3szh/files/osfstorage'

    json = fake_responses.files_node('f3szh', 'osfstorage',
                                     file_names=['hello.txt', 'bye.txt'],
                                     folder_names=['foo'])
    top_level_response = FakeResponse(200, json)

    second_level_url = ('https://api.osf.io/v2/nodes/9zpcy/files/' +
                        'osfstorage/foo123/')
    json = fake_responses.files_node('f3szh', 'osfstorage',
                                     file_names=['foo/hello2.txt',
                                                 'foo/bye2.txt'])
    second_level_response = FakeResponse(200, json)

    def simple_OSFCore_get(url):
        if url == store._files_url:
            return top_level_response
        elif url == second_level_url:
            return second_level_response

    with patch.object(OSFCore, '_get',
                      side_effect=simple_OSFCore_get) as mock_osf_get:
        files = list(store.files)

    assert len(files) == 4
    for file_ in files:
        assert isinstance(file_, File)
        assert file_.session == store.session

    # check right URLs are called in the right order
    expected = [((store._files_url,),), ((second_level_url,),)]
    assert mock_osf_get.call_args_list == expected


def test_create_existing_file():
    # test a new file at the top level
    new_file_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                    'osfstorage/foo123/')
    store = Storage({})
    store._new_file_url = new_file_url
    store._put = MagicMock(return_value=FakeResponse(409, None))

    fake_fp = MagicMock()
    with pytest.raises(FileExistsError):
        store.create_file('foo.txt', fake_fp)

    store._put.assert_called_once_with(new_file_url,
                                       data=fake_fp,
                                       params={'name': 'foo.txt'})

    assert fake_fp.call_count == 0


def test_create_new_file():
    # test a new file at the top level
    new_file_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                    'osfstorage/foo123/')
    store = Storage({})
    store._new_file_url = new_file_url
    store._put = MagicMock(return_value=FakeResponse(201, None))

    fake_fp = MagicMock()

    store.create_file('foo.txt', fake_fp)

    store._put.assert_called_once_with(new_file_url,
                                       data=fake_fp,
                                       params={'name': 'foo.txt'})

    assert fake_fp.call_count == 0


def test_create_new_file_subdirectory():
    # test a new file in a new subdirectory
    new_file_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                    'osfstorage/bar12/')
    new_folder_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                      'osfstorage/?kind=folder')
    store = Storage({})
    store._new_file_url = new_file_url
    store._new_folder_url = new_folder_url

    def simple_put(url, params={}, data=None):
        if url == new_folder_url:
            # this is a full fledged Folder response but also works as a
            # fake for _WaterButlerFolder
            return FakeResponse(
                201, {'data': fake_responses._folder('bar12', 'bar')}
                )
        elif url == new_file_url:
            # we don't do anything with the response, so just make it None
            return FakeResponse(201, None)
        else:
            print(url)
            assert False, 'Whoops!'

    fake_fp = MagicMock()

    with patch.object(Storage, '_put', side_effect=simple_put) as mock_put:
        store.create_file('bar/foo.txt', fake_fp)

    expected = [call(new_folder_url, params={'name': 'bar'}),
                call(new_file_url, params={'name': 'foo.txt'}, data=fake_fp)]
    assert mock_put.call_args_list == expected
    assert fake_fp.call_count == 0


def test_create_new_zero_length_file():
    # check zero length files are special cased
    new_file_url = ('https://files.osf.io/v1/resources/9zpcy/providers/' +
                    'osfstorage/foo123/')
    store = Storage({})
    store._new_file_url = new_file_url
    store._put = MagicMock(return_value=FakeResponse(201, None))

    fake_fp = MagicMock()
    fake_fp.peek = lambda x: ''

    store.create_file('foo.txt', fake_fp)

    store._put.assert_called_once_with(new_file_url,
                                       # this is the important check in
                                       # this test
                                       data=b'',
                                       params={'name': 'foo.txt'})

    assert fake_fp.call_count == 0
