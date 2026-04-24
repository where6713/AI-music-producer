# TASK-011 AC_35 Fallback Failure Evidence

- command: `python -c from src.main import produce; produce(raw_intent='配置异常显式失败验证', genre='都市流行', mood='克制释怀', vocal='any', profile='', lang='zh-CN', out_dir='out/task011_ac35_bad_config', verbose=False, dry_run=False)`
- return_code: 1
- expected: non-zero and explicit failure (no silent fallback)

## stdout_tail
```text

```

## stderr_tail
```text
    with request.urlopen(req, timeout=120) as resp:
         ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
  File "C:\Python313\Lib\urllib\request.py", line 189, in urlopen
    return opener.open(url, data, timeout)
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "C:\Python313\Lib\urllib\request.py", line 489, in open
    response = self._open(req, data)
  File "C:\Python313\Lib\urllib\request.py", line 506, in _open
    result = self._call_chain(self.handle_open, protocol, protocol +
                              '_open', req)
  File "C:\Python313\Lib\urllib\request.py", line 466, in _call_chain
    result = func(*args)
  File "C:\Python313\Lib\urllib\request.py", line 1367, in https_open
    return self.do_open(http.client.HTTPSConnection, req,
           ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                        context=self._context)
                        ^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python313\Lib\urllib\request.py", line 1322, in do_open
    raise URLError(err)
urllib.error.URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
```
