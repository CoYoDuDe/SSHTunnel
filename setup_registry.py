"""Addon-local safeguards for SetupHelper's restore metadata updates."""
import os
from pathlib import Path
import re
import secrets
import stat
import sys


def adapt(source):
    """Keep the installed helper, replacing its two self-truncating pipelines.

    Unknown helper layouts are rejected before Addon stops any service.
    A failed reverse patch must retain the shared file and all registrations.
    """
    if len(source)>65536 or not source.startswith('restoreActiveFile ()'):
        raise ValueError('Unsupported SetupHelper restore function')
    replacements={
        'grep -v "$packageName" "$packageList" | tee "$packageList" > /dev/null':
            'addonRemoveRegistryLine "$packageName" "$packageList"',
        'grep -v "$activeFile" "$installedFilesList" | tee "$installedFilesList" > /dev/null':
            'addonRemoveRegistryLine "$activeFile" "$installedFilesList"',
    }
    for before,after in replacements.items():
        if source.count(before)!=1:raise ValueError('Unsupported SetupHelper registry update')
        source=source.replace(before,after+' || { setInstallFailed "$EXIT_FILE_SET_ERROR" "Addon registry update failed"; return 1; }')
    pattern=r'if \$reversePatchError\s*;\s*then\s*\n.*?\n\s*fi\b'
    matches=list(re.finditer(pattern,source,re.S))
    if len(matches)!=1 or 'previousPatchesRoot' not in matches[0].group():
        raise ValueError('Unsupported SetupHelper reverse-patch fallback')
    source=source[:matches[0].start()]+(
        'if $reversePatchError; then\n'
        '    setInstallFailed "$EXIT_PATCH_ERROR" "Addon reverse patch failed; shared file and owners retained"\n'
        '    return 1\nfi')+source[matches[0].end():]
    return source


def remove_line(key,path):
    """Remove an exact line using a private stage and atomic replacement."""
    if os.geteuid()!=0:raise PermissionError('Root required for setup registry updates')
    if not key or len(key)>4096 or '\n' in key or '\r' in key:
        raise ValueError('Invalid registry key')
    path=Path(path)
    if not path.is_absolute() or path.parent.is_symlink():raise ValueError('Invalid registry path')
    parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    stage=None
    try:
        directory=os.fstat(parent)
        if directory.st_uid!=os.geteuid() or directory.st_mode & 0o022:
            raise ValueError('Unsafe registry directory')
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno());raw=stream.read(262145)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid()
                or info.st_nlink!=1 or info.st_mode & 0o022 or len(raw)>262144):
            raise ValueError('Unsafe registry file')
        data=b''.join(line for line in raw.splitlines(keepends=True) if line.strip()!=key.encode())
        candidate='.Addon-registry-'+secrets.token_hex(12)
        fd=os.open(candidate,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent)
        stage=candidate
        with os.fdopen(fd,'wb') as stream:
            os.fchown(stream.fileno(),info.st_uid,info.st_gid)
            os.fchmod(stream.fileno(),stat.S_IMODE(info.st_mode));stream.write(data)
            stream.flush();os.fsync(stream.fileno())
        current=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        if (current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns)!=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns):
            raise RuntimeError('Registry changed during update')
        named=os.stat(path.parent);held=os.fstat(parent)
        if (named.st_dev,named.st_ino)!=(directory.st_dev,directory.st_ino) or (held.st_dev,held.st_ino)!=(directory.st_dev,directory.st_ino):
            raise RuntimeError('Registry directory changed')
        os.replace(stage,path.name,src_dir_fd=parent,dst_dir_fd=parent)
        stage=None;os.fsync(parent)
    finally:
        try:
            if stage is not None:os.unlink(stage,dir_fd=parent)
        finally:
            os.close(parent)


if __name__=='__main__':
    try:
        if sys.argv[1:] == ['adapt']:print(adapt(sys.stdin.read(65537)),end='')
        elif len(sys.argv)==4 and sys.argv[1]=='remove':remove_line(sys.argv[2],sys.argv[3])
        else:raise ValueError('Invalid registry operation')
    except (OSError,ValueError,RuntimeError) as exc:
        print('Addon: '+str(exc),file=sys.stderr);raise SystemExit(245)
