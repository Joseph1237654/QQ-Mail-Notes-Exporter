from qq_notebook_exporter.filenames import build_note_filename, safe_filename_stem


def test_safe_filename_removes_windows_invalid_characters() -> None:
    assert safe_filename_stem('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_safe_filename_handles_reserved_names_and_trailing_space() -> None:
    assert safe_filename_stem("CON. ") == "_CON"
    assert safe_filename_stem("") == "无标题"


def test_safe_filename_truncates_without_trailing_dot() -> None:
    stem = safe_filename_stem("标题" * 80 + ".", max_length=20)
    assert len(stem) <= 20
    assert not stem.endswith((" ", "."))


def test_note_filename_keeps_title_and_unique_note_id() -> None:
    assert build_note_filename("会议记录", "_3012") == "会议记录__3012.docx"
    assert build_note_filename("会议记录", "_3013") == "会议记录__3013.docx"
