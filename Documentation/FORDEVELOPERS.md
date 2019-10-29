# Tapestry Specialist Backup Tool - User Documentation
*General-Use Documentation, prepared for Version 2.0.2*

The goal of this specific documentation file is to provide function-level understanding of the operation of Tapestry for contributors to the project and custom use-case implementations. For general use cases, runtime information can be found in `FORUSERS.md`. More information about special use cases and considerations can be found in `FORADMINS.md`.

## New in this version
The whole document, really.

## Classes
For code-level visibility, all tapestry classes are in `tapestry/classes.py`

### tapestry.Block *class*
The Block class is a construct used to analogize a "block" of files for tapestry to package into a single output file. Moving to the use of the Block object over the prior method (writing in directories to temp) offered significant performance improvement and reduction in overhead.

#### Init Method
```python3
tapestry.Block(name, max_size, count, smallest)
```
Returns an instantiated block object with the following properties:
- **name (string)**: The name of the block including its output filename.
- **max_size (int)**: a number of bytes that represents the maximum size of the plaintext, uncompressed block. This value is used to calculate whether or not a block can accept arbitrary new files that are submitted through `Block.put()`.
- **count (int)**: A sequence number for the block out of the full set of blocks used.
- **smallest (int)**: The size in bytes of the smallest file in the backup list. Used together with max_size to determine if the block is full during put operations.

#### Put Method
```python
tapestry.Block.put(file_identifier, file_index_object)
```
This adds a metadata record to the block for a particular file that is to be considered part of it, after determining if there is remaining space for that file in the block, and whether or not the block should simply be treated as full. The following arguments are expected:
- **file_identifier (string)**: A key used to retrieve this file's information later. Can be any string, but in Tapestry runtime this will be a UUID Type 4.
- **file_index_object**: The dictionary object comprising metadata about the file in question. While any dictionary will be accepted, Tapestry's runtime expects a dictionary in the following format in order to stay compliant with NewRIFF:
```python3
file_index_object = {
                        'fname': str("The proper name of the file, for example FORDEVELOPERS.md"), 
                        'sha256': str("A hex digest of the SHA256 hash of the contents of the file."),
                        'category': str("The key to look up in the categories dictionary, which is built during parse_config"),
                        'fpath': str("The path of the file below its category path, ie only sub-dirs of the category dir, including the filename."),
                        'fsize': int("File size in Bytes")
                        }
```

**Note on operation**: While the other aspects of the file_index_object are ultimately arbitrary, 'fsize' is required as it is used to determine if the file will fit in the block or not.

**Returns**: `True` if the file was placed into the block's register, `False` otherwise.

#### Meta Method
```python3
tapestry.Block.meta(sum_blocks, sum_size, sum_files, datestamp, comment_string, full_index, drop_dir)
```
Given sufficient external information, this creates the NewRIFF recovery index and drops it off at drop_dir for any given block. The following arguments are expected:
- **sum_blocks (int)**: The total number of blocks in the run.
- **sum_size(int)**: The total sum size in bytes of all files to be included in the backup.
- **sum_files(int)**: The total number of files included in the backup across all blocks.
- **datestamp(str)**: A vaguely-ISO-compliant datestamp (could technically be any value), ideally the current day ie `"2019-10-10"`.
- **comment_string(str)**: A comment string to be added to the metadata block. If `None`, a bland default is used. Functionality to actually populate this value is not currently part of Tapestry or on the roadmap.
- **full_index(dict)**: Expects the output of `tapestry.build_ops_list`. This becomes the value of the index key of the corresponding RIFF file.
- **drop_dir(str)**: Some path, ideally absolute, that will contain the output files.

**Note on operation**: The final output file will have the name `self.name+".riff"`

**Returns**: String of the final output path, including filename.

### tapestry.ChildProcess class
This class serves as a minimally-initialized child process. It is a subclass of `multiprocessing.Process`.

#### Init Method
```python3
tapestry.ChildProcess(queue_tasking, queue_complete, working_directory, locks, debug=False)
```
Create a child/worker process with the minimum of information required to function:
- **queue_tasking (mp.JoinableQueue)**: A joinable queue containing actionable tasks from which the child process will feed after being started.
- **queue_complete (mp.JoinableQueue)**: A joinable queue containing feedback from tasks executed by the child process to the parent process.
- **working_directory (str)**: A path, ideally absolute, to the temporary working directory or other directory. The child process will take this for its current working directory.
- **locks(dict)**: A dictionary where each key indicates an `mp.Lock` obect for its value. Used on some occasions to control work flow to avoid colliding writes.
- **debug(boolean)**: Sets a debug flag within the child process - when this flag is set to `True`, in addition to normal debug feedback, the ChildProcess will put an exit message into `queue_complete` when exiting.

**Note on operation**: The current locking infrastructure is supported only in windows

**Returns**: an instance of `tapestry.ChildProcess`

#### Run Method
```python3
tapestry.ChildProcess.run()
```
Consume tasks from `self.queue` (queue_tasking) repeatedly. In addition to executing the task by triggering its "call" method, the child process will also place any return from the task into `self.ret` (queue_complete). If the task pulled from the queue is `None`, the Child Process will exit.

**Note on operation**: If `TypeError` is raised when calling the next task, a message is placed into the return queue indicating that something unexpected has happened as a result.

**Returns**: Nothing.

### tapestry.FTP_TLS class
This is a simple override of `ftplib.FTP_TLS`, modifying `ntransfercmd` method to allow correct functioning with regard to the way the socket is wrapped, and allow FTP over TLS to work correctly in Tapestry's context. This is included with thanks to hynekcer

FTP_TLS is to be deprecated in the next feature release of Tapestry.

### tapestry.RecoveryIndex class
Special utility class for loading and translating Tapestry recovery index files and presenting them back to the script in a universal way. Made for both the old Recovery Pickle design as well as the NewRIFF format.

#### init Method
```python3
tapestry.RecoveryIndex(index_file)
```
Create a RecoveryIndex object out of the index file which conviently wraps a lot of index-related tasks:
- **queue_tasking (handle)**: A readable file handle (such as returned by the `open` built-in).

**Note on Operation**: As stated, this class will accept either the NewRIFF or Recovery Pickle designs. It does so by first trying to unpickle the contents of the file. If it fails to do so, it will attempt to load the JSON object by deserializing it. This will raise `tapestry.RecoveryIndexError` if the file consumed is not valid.

**Returns**: an instance of `tapestry.RecoveryIndex`

#### find Method
```python3
tapestry.RecoveryIndex.find(file_key)
```
Attempts to find `file_key` as a key in the index of files, returning important metadata needed to restore it:
- **file_key(str)**: A file ID (in normal operation, UUID) which is expected to be in the file index.

**Note on operation**: While this can't/shouldn't happen under runtime conditions (unless the index is damaged/modified somehow), if thereis a `KeyError` while attempting to retrieve the information necessary, the output tuple will be `(b'404', b'404')`

**Returns**: A tuple of `file_category` (sufficient to look up the top of the category path) and `sub_path`, which is the full output path for the file including the filename. A full join would be to use `os.path.join` on the category path and `sub_path`.

### RecoveryIndexError class
An exception raised under a small number of conditions for the RecoveryIndex class - it is otherwise unremarkable.

### Task Classes
The `Task` series of classes are all children of python's `object` builtin. They all have the same common functionality:
- Necessary information for their operation to be provided to the init call
- The task itself is triggered by calling the instantiated class as though it were a function, with no additional arguments.

Due to this simplification they are described more compactly below.

#### TaskCheckIntegrity
```python3
tapestry.TaskCheckIntegrity(tar_file, fid, kg_hash)
```
Evaluate a target file (within a specific tarred Block) to determine if it matches a known-good hash for the file:
- **tar_file (str)**: Absolute path to a tar file (compressed or otherwise) which will contain the target file
- **fid (str)**: The filename in the archive which is being checked.
- **kg_hash (str)**: The value of `RecoveryIndex["index"]["somefile"]["sha256"]`, which is the at-packing known-good hash for the file.

**Note on Operation**: *Class implemented but non-functional in v 2.0.2*. This function would only be possible while reading in a RecoveryIndex that was populated from a NewRIFF document.

**Returns**: List of a boolean and string, each indicating whether or not the file hashes matched.

#### TaskCompress
```python3
tapestry.TaskCompress(t, lvl)
```
Takes the target file and copies it to a new location after applying a configured level of BZ2 compression:
- **t (str)**: Absolute path to a target file; intentionally, a tarball to be compressed.
- **lvl(int)**: An integer value from 1-9 indicating the desired compression level

**Note on Operation**: This class leverages `shutil.copyfileobj` to execute a buffered copy/compression flow, allowing for arbitrarily large compression jobs while minimizing the compression overhead.

**Returns**: String indicating the file was compressed, along with input and output filenames.

#### TaskDecompress
```python3
tapestry.TaskDecompress(t)
```
Takes the target file and copies it to a new location after applying a configured level of BZ2 compression:
- **t (str)**: Absolute path to a target file; intentionally, a tarball to be decompressed.

**Note on Operation**: We look for magic bytes at the beginning of the file to determine if this is a BZ2 compressed object. If not, it will be skipped. The specific check is to see if the first 3 bytes of the file match `b"BZh"`. This check is required because completely-uncompressed .tap files are permitted under the standard runtime.

**Returns**: String indicating the file was decompressed, or decompression was skipped.

#### TaskEncrypt
```python3
tapestry.TaskEncrypt(t, fp, out, gpg)
```
Takes the target file and copies it to a new location after encrypting it against a target GPG key, using system GPG defaults:
- **t (str)**: Absolute path to a target file; intentionally, an archive to encrypt.
- **fp (str)**: A GPG key fingerprint (or other unique identifier) to be passed as an argument to GPG. This will point at the **public key** which file `t` is to be encrypted against.
- **out (str)**: A path to the output directory, usually not the same as the working directory.
- **gpg (gnupg.GPG)**: An instance of the GPG handler introduced by `python-gnupg`, for which the key indicated by `fp` must be on the keyring.

**Note on Operation**: As coded, this function will output the encrypted version of `t`, with the file extension changed to `.tap`, as an ascii-armoured file dropped in the directory indicated by `out`. The key indicated by the FP is set to be trusted regardless of its trust status of the keyring. **#FUTURE**: Further work and consideration should go into ensuring the integrity of the Tapestry config file.

**Returns**: String indicating the file was encrypted, or, if something went wrong, string indicating the cause of failure.

#### TaskDecrypt
```python3
tapestry.Taskdecrypt(block, working_directory, gpg)
```
Takes the target file and writes its cleartext form into a specified working directory:
- **block (str)**: Absolute path to a target file; intentionally, an archive to decrypt.
- **working_directory (str)**: The working directory to output the cleartext version of the file to. Ostensibly this should likely be the same as the working directory for the ChildProcess instance processing these tasks, but it's set by `__main__` and can be any value.
- **gpg (gnupg.GPG)**: An instance of the GPG handler introduced by `python-gnupg`, for which the key indicated by `fp` must be on the keyring.

**Note on Operation**: Like the encryption Task, this Task has `always_trust=True` set among its various arguments. This is because the signature validity is checked during an earlier part of the runtime, in which manual trust verification was asserted. No credential for the key is expected in the Task call - the gpg-agent binary on the local system will trigger whatever `pinentry` binary is expected, instead, as necessary. This avoids Tapestry ever handling a key credential

**Returns**: String indicating the file was decrypted, or, if something went wrong, string indicating the cause of failure.

#### TaskSign
```python3
tapestry.TaskSign(t, fp, out, gpg)
```
Takes the target file and outputs a detached PGP signature for a given FP.:
- **t (str)**: Absolute path to a target file; intentionally, an archive to encrypt.
- **fp (str)**: A GPG key fingerprint (or other unique identifier) to be passed as an argument to GPG. This will point at the **private key** used to sign the target file.
- **out (str)**: A path to the output directory, usually not the same as the working directory.
- **gpg (gnupg.GPG)**: An instance of the GPG handler introduced by `python-gnupg`, for which the key indicated by `fp` must be on the keyring.

**Note on Operation**: As coded, this will output an armoured signature. No credential for the key is expected in the Task call - the gpg-agent binary on the local system will trigger whatever `pinentry` binary is expected, instead, as necessary. This avoids Tapestry ever handling a key credential

**Returns**: String indicating the file was signed or, if something went wrong, string indicating the cause of failure.

#### TaskTarBuild
```python3
tapestry.TaskTarBuild(tarf, fid, path, bname)
```
Takes the target file and outputs a detached PGP signature for a given FP.:
- **tarf (str)**: Absolute path to a destination tarball. If not extant, it will be created.
- **fid (str)**: A file ID. This ID should be the same as the key that will pull this file's description out of a riff-based index's lookup tables, but for other applications is arbitrary. The file will be stored in the tarball with this value as its filename.
- **path (str)**: Relative or absolute (ideally absolute) path to the target file.
- **bname (str)**: A string, usually the name of the block, which is used against the locks dictionary (global at the child process level) to fetch the appropriate lock.

**Note on Operation**: *This function is only tested/intended for use under unix and its name will likely be refactored in the future to indicate this*. The principal limitation there is the inheritance of locks between child processes in Windows, which works significantly differently enough that a whole other class of solution will need to be found. The locks prevent tasks from running into each other and attempting to write to the same tarfile simultaneously, which would obviously cause issues.

**Returns**: String indicating which file was added to which block.

### TaskTarUnpack
```python3
tapestry.TaskTarUnpack(tar, fid, category_dir, path_end)
```
Takes the target file and outputs a detached PGP signature for a given FP.:
- **tarf (str)**: Absolute path to a source tarball.
- **fid (str)**: An identifier specifying a unique file within the tarball to unpack.
- **category_dir (str)**: The top-level or "categorical" directory for a file as pulled from config or reconstructed by the fallback logic. This serves as the upper portion of the final output path.
- **path_end (str)**: A path, relative to the category_dir, where the file will be placed, including the final name of the file in question.

**Note on Operation**: Unlike the TaskTarBuild, TaskTarUnpack doesn't rely on locks to function and can be called on any platform. The behaviour of the unpack is to extract the file to its final destination before renaming it to its original filename.

**Returns**: String indicating which file was put where.

## Functions
For code-level visibility, all tapestry classes are in `tapestry/__main__.py`.

### announce
```python3
tapestry.announce()
```
Print's tapestry's welcome pages to stdout, including a dynamic version number.

**Note on Operation**: If the global debug value is set, such as by `--debug` at runtime, this will also print the current OS.
**Returns**: Nothing.

### build_ops_list
```python3
tapestry.build_ops_list(namespace)
```
Takes the given namespace and performs the "build ops list" operations, which is the bulk of metadata gathering for forming NewRiff backup indexes, and the operation of the rest of the application. Expects:
- **namespace(object)**: Tapestry's namespace is literally just an instance of object() with various attributes added. In total, build_ops_list expects the object to have been fully populated by `parse_args` and `parse_config`.

**Returns**: `file_index`, a dictionary forming the "index" key of the eventual metadata pack.

### build_recovery_index
```python3
tapestry.build_recovery_index(ops_list)
```
Parses ops_list in order to create a sorted list of file IDs sufficient to perform the blocksort algorithm, used later in the application to provide the smallest number of output files. Expects:
- **ops_list (dict)**: The output of tapestry.build_ops_list.

**Returns**: `working_index`, a sorted list of file IDs, which were sorted based on file size in descending order, and `sum_size`, being the sum of all file sizes included in this backup.

### clean_up
```python3
tapestry.clean_up(working_directory)
```
Gracefully handling errors, delete the contents of a target working directory, including the directory itself. Intended use case is to remove the temporary working directory tapestry uses. Expects:
- **working_directory (str)**: absolute path to a directory to be removed.

**Returns**: Nothing

### compress_blocks
```python3
tapestry.compress_blocks(ns, targets, do_compression=True, compression_level=1)
```
This is one of the "workhorse" functions of Tapestry as an application. It handles the etablishment of the worker pools and queues needed to perform the compression operation, along with managing that actual process and printing the status display information to stdout. Expects:
- **ns (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **targets (list)**: A list of absolute paths to the files to be compressed.
- **do_compression (boolean)**: Whether or not to actually enact compression, or simply skip through execution.
- **compression_level (int)**: An integer number from 1-9 representing the BZ2 compression level to use.

**Note on Operation**: This whole function is includes in an `if name main` statement.

**Returns**: A list of files to be encrypted - this is the logical next step in the operation of the application.

### debug_print
```python3
tapestry.debug_print(msg)
```
This function looks for a global debug variable. If it is not set or True, the function then prints the contents of `msg`
- **msg (str)**: Message to be printed to stdout

**Note on Operation**: The ability to print if the global debug is not set was added in 2.0.2 to support the new unit tests.

**Returns**: Nothing.

### decompress_blocks
```python3
tapestry.decompress_blocks(namespace)
```
This is one of the "workhorse" functions of Tapestry as an application. It handles the establishment of the worker pools and queues needed to perform the decompression operation, along with managing that actual process and printing the status display information to stdout. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.

**Note on Operation**: This whole function is included in an `if name main` statement for sanity reasons.

**Returns**: Nothing

### decrypt_blocks
```python3
tapestry.decrypt_blocks(ns, verified_blocks, gpg_agent)
```
This is one of the "workhorse" functions of Tapestry as an application. It handles the establishment of the worker pools and queues needed to perform the decryption operation, along with managing that actual process and printing the status display information to stdout. Expects:
- **ns (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **verified_blocks (list)**: a list of file paths to decrypt. These blocks will be implicitly trusted so this list should be provided by tapestry.verify_blocks.
- **gpg_agent (object)**: an instance of `gnupg.GPG` to serve as the GPG agent shared among the worker process.

**Note on Operation**: This whole function is included in an `if name main` statement for sanity reasons. *Security*: Decrypt blocks uses the always_trust override during decryption and cannot verify its own signiatures. It is hazardous to feed it anything other than a list of target blocks that have already had their signatures verified.

**Returns**: Nothing

### do_main
```python3
tapestry.do_main(ns, gpg_agent)
```
This function essentially gates the entire backup workflow of the runtime, providing the core logic to call the relevant functions in the correct order, while managing state. 

Expects:
- **ns (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **gpg_agent (object)**: an instance of `gnupg.GPG` to serve as the GPG agent shared among the worker process.

**Note on Operation**: This involves (loosely) the following:
- calling `build_ops_list` to feed `build_recovery_index`
- determines the host platform, and runs the appropriate pack_blocks function
- `compress_blocks`
- `encrypt_blocks`
- `sign_blocks`
- If so configured, depositing the blocks with `ftp_deposit_files`
- Finally, calling `cleanup` and `exit()`


**Returns**: Nothing

### do_recovery
```python3
tapestry.do_recovery(ns, gpg_agent)
```
This function essentially gates the entire recovery workflow of the runtime, providing the core logic to call the relevant functions in the correct order, while managing state. 

Expects:
- **ns (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **gpg_agent (object)**: an instance of `gnupg.GPG` to serve as the GPG agent shared among the worker process.

**Note on Operation**: This involves (loosely) the following:
- using the appropriate retrieval functions (ftp or media) depending on local config.
- triggering an interactive verification loop for those signiatures
- `decrypt_blocks`
- `Decompress_blocks`
- `unpack_blocks`
- Finally, calling `cleanup` and `exit()`


**Returns**: Nothing

### encrypt_blocks
```python3
tapestry.encrypt_blocks(targets, gpg_agent, fingerprint, namespace)
```
This is one of the "workhorse" functions of Tapestry as an application. It handles the establishment of the worker pools and queues needed to perform the encryption operation, along with managing that actual process and printing the status display information to stdout. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **targets (list)**: A list of files to be encrypted
- **gpg_agent (object)**: an instance of `gnupg.GPG` to serve as the GPG agent shared among the worker process.
- **fingerprint (string)**: A unique identifier for a particular key available to GPG-agent as at least a public key, and against which the files specified in `targets` will be encrypted. 

**Note on Operation**: This whole function is included in an `if name main` statement for sanity reasons.

**Returns**: Nothing

### ftp_deposit_files
```python3
tapestry.ftp_deposit_files(namespace)
```
This function is the workflow-manager for sending files to the remote FTP after the rest of the backup runtime is completed. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.

**Note on Operation**: This function crawls `namespace.drop`, the Tapestry output directory, and sends all files ending in `.tap` or `.sig` to the FTP configured in the config. It does this by leveraging ftp_establish_connection and ftp_send_block. Also, it will delete the files it sends unless the configuration file indicates it should retain local copies, as a consideration to future automation improvements. This function might be retained more or less intact in #FUTURE, when the transition to SFTP is complete.

**Returns**: Nothing

### ftp_establish_connection
```python3
tapestry.ftp_establish_connection(url, port, ssl_context, username, password)
```
It seemed logical to create a single function for creating FTP connections regardless of final intended operation. Expects:
- **url (str)**: URL, IP, or Hostname to be used to address a specific target FTP or FTP/S Server
- **port (int)**: The appropriate tcp port number to use for the connection. If not provided, will default to `21`.
- **ssl_context (object)**: The return of `tapestry.get_ssl_context`. If present, FTP/S is in use. Otherwise, the application defaults to normal FTP.
- **username (str)**: The username to use at the remote host for authentication.
- **password (str)**: The password required to authenticate as `username`

**Note on Operation**: This function will determine the appropriate connection type (FTP vs FTP/S) prior to connecting. If FTP/S, the connection will then be authenticated, raising `ConnectionRefusedError` if the handshake fails. All else being well, the connection function will then login using the username/password provided, if any. #FUTURE work in 2.1 will replace this function entirely with a similar function that negotiates SFTP.

**Returns**: The FTP connection object, which can then be passed to other, specific functions.

### ftp_fetch_block
```python3
tapestry.ftp_fetch_block(fname, ftp_connect, dir_destination)
```
This simplistic function is a wrapper for retrieving one file from an FTP connection and placing it back on the local disk. Expects:
- **fname (str)**: Remote name of the file to be retrieved.
- **ftp_connect (object)**: An FTP connection, ideally the type returned by `tapestry.ftp_establish_connection()`
- **dir_destination (str)**: Destination directory to drop off the file once downloaded.

**Note on Operation**: The final output file will be at `os.path.join(dir_destination, fname)`. #FUTURE work will probably deprecate this function entirely.

**Returns**: Nothing.

### ftp_grep_blocks
```python3
tapestry.ftp_grep_blocks(label, date, ftp_connect)
```
This simplistic function is a wrapper for listing files on a remote server based on a simple filter. Expects:
- **label (str)**: A machine label for which we are looking for blocks.
- **date (str)**: A date for which we are looking for blocks.
- **ftp_connect (object)**: An FTP connection, ideally the type returned by `tapestry.ftp_establish_connection()`

**Note on Operation**: #FUTURE work will probably deprecate this function entirely, or else massively change its behaviour.

**Returns**: An integer count of the files located, plus a list thereof (for retrieval.)

### ftp_retrieve_files
```python3
tapestry.ftp_deposit_files(namespace, gpg)
```
This function handles the full workflow of retrieving .tap files and their signatures from the remote FTP or FTP/S server.  Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **gpg_agent (object)**: an instance of `gnupg.GPG` to serve as the GPG agent in order to decrypt metadata files.

**Note on Operation**: This is largely interactive, displaying available dates and then using user input to determine the right restore point. It does this by leveraging ftp_establish_connection, ftp_grep_block and ftp_fetch_block. This function might be retained more or less intact in #FUTURE, when the transition to SFTP is complete.

**Returns**: Namespace, after appending the recovery index extracted as part of this process.

### ftp_send_block
```python3
tapestry.ftp_send_block(fname, ftp_connect, dir_destination)
```
This simplistic function is a wrapper for copying a file from local storage onto the remote host. Expects:
- **fname (str)**: The local filename (including the full path) to be retrieved.
- **dir_destination (str)**: Destination directory to use on the remote host.
- **ftp_connect (object)**: An FTP connection, ideally the type returned by `tapestry.ftp_establish_connection()`

**Note on Operation**: #FUTURE work will probably deprecate this function entirely, as FTP/S support is being deprecated overall in 2.1

**Returns**: Nothing.

### generate_keys
```python3
tapestry.generate_keys(namespace, gpg_agent)
```
Generates a new key, writing the fingerprint both into the namespace and then directly into the config file.. Expects:
- **namespace (object)**: Tapestry's populated namespace object.
- **gpg_agent (object)**: A `gnupg.GPG` object instantiated to have access to the local keyring.

**Note on Operation**: Some strange errors still exist when calling this function under unusual use cases and #FUTURE work should focus on correcting these. At present the only known bug involves using --genKey when the key in the config file at the start of runtime cannot be found on the keyring - genkey will complete and update the config, but then the whole script needs to be recalled.

**Returns**: The updated namespace object.

### get_ssl_context
```python3
tapestry.get_ssl_context(ns, test=False)
```
Fetches an appropriately-configured SSL Context to use in setting up FTP/S functions. Expects:
- **ns (object)**: Tapestry's populated namespace object.
- **test (boolean)**: If true, uses a local certificate for the trusted root rather than any actual true trusted store.

**Note on Operation**: # Future will certainly deprecate this.

**Returns**: An SSLContext object.

### media_retrieve_files
```python3
tapestry.media_retrieve_files(mountpoint, temp_path, gpg_agent)
```
Introspects the mountpoint location, identifying any tapestry blocks and signatures. It also recovers a recovery index from the first block it finds and uses that to ensure it has all the appropriate components. Expects:
- **mountpoint**: A path (usually either `/media/` or a drive letter) determining where the function should begin looking for blocks.
- **temp_path**: A path, hopefully absolute, to a working directory intended to be temporary. Under normal operation this will later be erased using `tapestry.cleanup()`
- **gpg_agent (object)**: A `gnupg.GPG` object instantiated to have access to the local keyring.

**Note on Operation**: The simplistic nature of the existing MRF function makes a critical assumption: only tap blocks from ONE recovery set will be at the mountpoint. This wasn't unreasonable when the original design of burning blocks to optical disks was in play, but it may be an issue now. #FUTURE work should look at enhancements to this.

**Returns**: The `tapestry.RecoveryIndex` file that was created during this process.

### parse_args
```python3
tapestry.parse_args(namespace)
```
This both sets up the argument parser (and, by extension, the output for `python3 -m tapestry --help`), and also parses the arguments, attaching them to namespace, which is the usual tapestry namespace argument.

The current arguments supported are:
- `--rcv`: Recover a previous archive from disk.
- `--inc`: Tells the system to include non-default sections in the backup process, that is, the "Additional Locations" list.
- `--debug`: Increase output verbosity.
- `--genKey`: Generates a new key before proceeding with any other functions called.
- `--devtest`: Starts in testing mode -- sets a lot of additional debugging and test flags, as well as `--debug`
- `-c`: absolute or relative path to the config file

**Returns**: The modified namespace object.

### parse_config
```python3
tapestry.parse_config(namespace):
```
Uses configparser to read the configuration file that was identified during `parse_args`, and appends both information from that file and some platform-specific information into namespace, which is the usual Tapestry namespace object. For obvious reasons, anything to be added to the config should be added here. For less obvious reasons related to consistency, anything to be requested from the os or system modules related to the run should also be added here.

**Returns**: The updated namespace object.

### sign_blocks
```python3
tapestry.sign_blocks(namespace, gpg_agent)
```
Locates every .tap file in `namespace.drop` and signs it using the default signing key set up in config. Expects:
- **namespace (object)**: Tapestry's populated namespace object.
- **gpg_agent (object)**: A `gnupg.GPG` object instantiated to have access to the local keyring.

**Note on Operation**: Like all the other `_blocks` functions, this is a workhorse function that spawns workers, sets up queues, and manages the overall multiprocessing flow it operates.

**Returns**: Nothing.

### start_gpg
```python3
tapestry.start_gpg(namespace)
```
Locates every .tap file in `namespace.drop` and signs it using the default signing key set up in config. Expects:
- **namespace (object)**: Tapestry's populated namespace object.

**Note on Operation**: In debug or devtest modes, this function will set gnupg.GPG's verbose flag to True.

**Returns**: The instantiated object to set as gpg_agent for the other functions in Tapestry.

### status_print
```python3
tapestry.status_print(done, total, job, message):
```
Pretty-prints a status bar during a given operation. Expects:
- **done (int)**: The total number of individual tasks completed.
- **total (int)**: The sum of all jobs expected to be completed.
- **job (str)**: A job, such as "Encrypting", to be displayed next to the status bar to give some indication of what is being done.
- **message (str)**: A special message to be displayed. Most uses show `Working...`

**Note on Operation**: In debug or devtest modes, this function will set gnupg.GPG's verbose flag to True.

**Returns**: The instantiated object to set as gpg_agent for the other functions in Tapestry.

### unix_pack_blocks
```python3
tapestry.unix_pack_blocks(sizes, ops_list, namespace):
```
This is one of the "workhorse" functions of Tapestry as an application. It handles the establishment of the worker pools and queues needed to perform the block-building and then Tarring process, along with managing that actual process and printing the status display information to stdout. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **sizes (list)**: A list of file identifiers, sorted by what had been their size, which corresponds to the keys of `ops_list`. This is returned by `tapestry.build_recovery_index`.
- **ops_list (dict)**: A full ops list such as returned by `tapestry.build_ops_list`

**Note on Operation**: This is the only multiprocessing operation that cannot be ported directly to the `win32` system, because of its reliance on locks to avoid write collisions, and the corresponding and so far unsolved issue of lock inheritance on windows.

**Returns**: A list of the created tarball files for use in later steps of the process.

### unpack_blocks
```python3
tapestry.unpack_blocks(namespace):
```
This is one of the "workhorse" functions of Tapestry as an application. It handles the establishment of the worker pools and queues needed to perform the block-building and then Tarring process, along with managing that actual process and printing the status display information to stdout. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.

**Note on Operation**: Files to unpack are found by looking for tars in the working directory.

**Returns**: Nothing

### verify_blocks
```python3
tapestry.verify_blocks(namespace, gpg_agent, testing=False):
```
This is one of the "workhorse" functions of Tapestry as an application. It handles special cases for verification. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **gpg_agent (object)**: A `gnupg.GPG` object instantiated to have access to the local keyring.
- **testing (bool)**: If true, essentially automatically trusts every signiature. This is bad from a use perspective but is necessary for unit testing to proceed without the need for manual intervention on behalf of the tester.

**Note on Operation**: This verification process allows for a speration between local keyring trusts and "actual" trust levels. It's particularly useful in situations where differing trust levels are in use. Specifically, it requires the fingerprint of the signing key to be explicitly validated during recovery, avoiding an attack where a falsely-trusted key was placed into config or onto the keyring prior to recovery.

**Returns**: Nothing

### verify_keys
```python3
tapestry.verify_blocks(namespace, gpg_agent)
```
A simplistic function to catch early on if the configured keys are missing. If that is the case, the application exits. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **gpg_agent (object)**: A `gnupg.GPG` object instantiated to have access to the local keyring.

**Returns**: Nothing

### windows_pack_blocks
```python3
tapestry.windows_pack_blocks(sizes, ops_list, namespace):
```
This is one of the "workhorse" functions of Tapestry as an application. It handles the block-sort functionality and tarring of block files - unlike the unix version, this version executes linearly in a single process to avoid write collisions. Expects:
- **namespace (object)**: Tapestry's special-purpose namespace object, which by this point has been fully populated with all the relevant attributes.
- **sizes (list)**: A list of file identifiers, sorted by what had been their size, which corresponds to the keys of `ops_list`. This is returned by `tapestry.build_recovery_index`.
- **ops_list (dict)**: A full ops list such as returned by `tapestry.build_ops_list`

**Note on Operation**: #FUTURE work in 2.1 will contrive a way to do this in a multiprocessed fashion, which should derive a massive performance improvement over the current, linear model

**Returns**: A list of the created tarball files for use in later steps of the process.