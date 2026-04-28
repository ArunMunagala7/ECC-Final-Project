# System Architecture - NFS+SSH Distributed Video Processing

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│                    (video.mp4, strategy)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MASTER NODE                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Main Controller (main.py)                               │  │
│  │  • Loads configuration                                   │  │
│  │  • Creates workers (RemoteWorker/LocalWorker)           │  │
│  │  • Health checks workers before processing              │  │
│  │  • Initiates processing pipeline                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────┬───────────┴──────────┬────────────┐           │
│  │            │                       │            │           │
│  ▼            ▼                       ▼            ▼           │
│  Segmenter  Scheduler              Merger      Monitor         │
│  (split)    (assign+retry)        (combine)   (track)          │
└──┬────────────┬─────────────────────┬────────────────────────┬─┘
   │            │                     │                        │
   │            │                     │                        │
   │     ┌──────┴──────┐              │                        │
   │     │             │              │                        │
   │     │  Task Queue │              │                        │
   │     │  (dynamic)  │              │                        │
   │     └──────┬──────┘              │                        │
   │            │                     │                        │
   ▼            ▼                     ▼                        │
┌─────────────────────────────────────────────────────────────┐ │
│              NFS SHARED STORAGE                              │ │
│        /home/ubuntu/nfs_shared/                              │ │
│  ┌────────────┬────────────────┬──────────────┐            │ │
│  │  chunks/   │  processed/    │  output/     │            │ │
│  │  (input    │  (worker       │  (final      │            │ │
│  │  segments) │  outputs)      │  merged)     │            │ │
│  └────────────┴────────────────┴──────────────┘            │ │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘ │
       │              │              │              │           │
       │              │              │              │           │
       ▼              ▼              ▼              ▼           │
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│  WORKER 0 │  │  WORKER 1 │  │  WORKER 2 │  │  WORKER 3 │   │
│  ✓ Healthy│  │  ✓ Healthy│  │  ✗ Down   │  │  ✓ Healthy│   │
│  FFmpeg   │  │  FFmpeg   │  │           │  │  FFmpeg   │   │
│  Process  │  │  Process  │  │  (skipped)│  │  Process  │   │
│           │  │           │  │           │  │           │   │
│ .199      │  │ .58       │  │ .92       │  │ .111      │   │
└───────────┘  └───────────┘  └───────────┘  └───────────┘   │
       │              │              │              │           │
       └──────────────┴──────────────┴──────────────┘           │
                      │                                          │
                      └──────────────────────────────────────────┘
                                     │
                                     ▼
                            FINAL OUTPUT VIDEO
```

---

## Fault Tolerance Features

### 1. Worker Health Checks

Before processing begins, the system verifies each worker is reachable:

```
Health Check Process:
┌─────────────┐
│ Master      │
│ starts      │
└──────┬──────┘
       │
       ├─ SSH ping Worker 0  ───► ✓ Healthy
       ├─ SSH ping Worker 1  ───► ✓ Healthy
       ├─ SSH ping Worker 2  ───► ✗ Unreachable (network down)
       └─ SSH ping Worker 3  ───► ✓ Healthy
       │
       ▼
┌─────────────┐
│ Process with│
│ 3 workers   │
│ (skip #2)   │
└─────────────┘
```

**Implementation:**
- Simple SSH echo command: `ssh worker 'echo healthy'`
- 5-second timeout per worker
- Failed workers excluded from task assignment
- System continues with available workers

### 2. Task Retry Mechanism

Both static and dynamic scheduling retry failed tasks up to `max_retries=2`:

```
Task Failure & Retry Flow:
┌─────────────┐
│ Chunk 3     │
│ → Worker 1  │
└──────┬──────┘
       │
       ▼
   Processing...
       │
       ▼
   ✗ FAILED
   (timeout/error)
       │
       ▼
┌─────────────┐
│ Retry 1/2   │
│ → Worker 2  │  (reassign to next worker)
└──────┬──────┘
       │
       ▼
   Processing...
       │
       ▼
   ✗ FAILED
       │
       ▼
┌─────────────┐
│ Retry 2/2   │
│ → Worker 3  │
└──────┬──────┘
       │
       ▼
   ✓ SUCCESS
```

**Features:**
- Automatic task requeuing on failure
- Worker rotation (static) or queue resubmission (dynamic)
- Maximum 2 retry attempts per task
- Detailed logging of retry attempts

### 3. Result Validation

Before merging, the system validates all output chunks:

```
Validation Checks:
┌─────────────────┐
│ All chunks      │
│ processed       │
└────────┬────────┘
         │
         ▼
    Validation
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
    ▼         ▼        ▼        ▼
 Check     Check    Check    Check
 exists    size     size     exists
   │         │        │        │
   ▼         ▼        ▼        ▼
  ✓ OK     ✓ 2MB    ✗ 500b   ✓ OK
           VALID    CORRUPT  VALID
         │
         ▼
┌─────────────────┐
│ Merge only      │
│ valid chunks    │
│ (skip corrupt)  │
└─────────────────┘
```

**Checks:**
- File exists in processed directory
- File size > 1KB (not corrupted/empty)
- Warnings logged for invalid outputs
- Merge proceeds with valid chunks only

---

## Component Architecture

### 1. Master Node Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Master Node                             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  main.py (Entry Point)                               │  │
│  │  • Argument parsing (--input, --strategy, --remote)  │  │
│  │  • Configuration loading                             │  │
│  │  • Worker factory                                    │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                             │
│               ▼                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Master Coordinator (master/__init__.py)             │  │
│  │                                                       │  │
│  │  ┌─────────────────┐    ┌─────────────────┐         │  │
│  │  │ process_static()│    │ process_dynamic()│         │  │
│  │  │                 │    │                 │         │  │
│  │  │ • Pre-assign    │    │ • Create queue  │         │  │
│  │  │   chunks        │    │ • Workers pull  │         │  │
│  │  │ • Round-robin   │    │   tasks         │         │  │
│  │  │ • Fixed mapping │    │ • Load balance  │         │  │
│  │  └─────────────────┘    └─────────────────┘         │  │
│  │                                                       │  │
│  │  ThreadPoolExecutor                                  │  │
│  │  • Concurrent SSH command execution                  │  │
│  │  • Worker.process_task() in parallel                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Core Utilities (core/)                              │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ VideoSegmenter (segmenter.py)               │    │  │
│  │  │ • FFmpeg segmentation                       │    │  │
│  │  │ • Calculate segment count                   │    │  │
│  │  │ • Write chunks to NFS                       │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ VideoMerger (merger.py)                     │    │  │
│  │  │ • FFmpeg concat demuxer                     │    │  │
│  │  │ • Read processed chunks from NFS            │    │  │
│  │  │ • Write final output                        │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ VideoProcessor (processor.py)               │    │  │
│  │  │ • FFmpeg command builder                    │    │  │
│  │  │ • Check FFmpeg availability                 │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Worker Architecture

### Remote Worker (Cloud Execution)

```
┌─────────────────────────────────────────────────────────────┐
│                    RemoteWorker                              │
│                   (worker/__init__.py)                       │
│                                                              │
│  Attributes:                                                 │
│  • worker_id: 0-3                                           │
│  • ssh_host: 149.165.169.199 (example)                     │
│  • ssh_user: exouser                                        │
│  • ssh_key: ~/.ssh/id_rsa                                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  process_task(input_path, output_path)               │  │
│  │                                                       │  │
│  │  1. Build FFmpeg command                             │  │
│  │     ffmpeg -i {input} -c:v libx264 {output}         │  │
│  │                                                       │  │
│  │  2. Build SSH command                                │  │
│  │     ssh exouser@{host} 'ffmpeg ...'                 │  │
│  │                                                       │  │
│  │  3. Execute via subprocess.run()                     │  │
│  │                                                       │  │
│  │  4. Return execution time & success status           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  NFS Paths (accessible on worker VM):                       │
│  • Input:  /home/ubuntu/nfs_shared/chunks/chunk_XXX.mp4    │
│  • Output: /home/ubuntu/nfs_shared/processed/chunk_XXX.mp4 │
└─────────────────────────────────────────────────────────────┘
```

### Local Worker (Testing)

```
┌─────────────────────────────────────────────────────────────┐
│                     LocalWorker                              │
│                   (worker/__init__.py)                       │
│                                                              │
│  Attributes:                                                 │
│  • worker_id: 0-2                                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  process_task(input_path, output_path)               │  │
│  │                                                       │  │
│  │  1. Build FFmpeg command                             │  │
│  │     ffmpeg -i {input} -c:v libx264 {output}         │  │
│  │                                                       │  │
│  │  2. Execute locally via subprocess.run()             │  │
│  │                                                       │  │
│  │  3. Return execution time & success status           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Local Paths:                                               │
│  • Input:  /tmp/video_processing/chunks/chunk_XXX.mp4      │
│  • Output: /tmp/video_processing/processed/chunk_XXX.mp4   │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Static Scheduling Flow

```
                    ┌─────────────┐
                    │ Input Video │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Segmenter  │
                    │ (6 segments)│
                    └──────┬──────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Pre-assignment │
                  │  (Round-robin) │
                  └────────┬───────┘
                           │
         ┌─────────────────┼─────────────────┬──────────────┐
         │                 │                 │              │
         ▼                 ▼                 ▼              ▼
    Chunk 0,4         Chunk 1,5         Chunk 2          Chunk 3
         │                 │                 │              │
         ▼                 ▼                 ▼              ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐   ┌─────────┐
    │Worker 0 │      │Worker 1 │      │Worker 2 │   │Worker 3 │
    │         │      │         │      │         │   │         │
    │ 2 tasks │      │ 2 tasks │      │ 1 task  │   │ 1 task  │
    │(fixed)  │      │(fixed)  │      │(fixed)  │   │(fixed)  │
    └────┬────┘      └────┬────┘      └────┬────┘   └────┬────┘
         │                │                 │              │
         └────────────────┴─────────────────┴──────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Merger   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Final Output │
                    └─────────────┘
```

### Dynamic Scheduling Flow

```
                    ┌─────────────┐
                    │ Input Video │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Segmenter  │
                    │ (6 segments)│
                    └──────┬──────┘
                           │
                           ▼
                  ┌────────────────┐
                  │   Task Queue   │
                  │ [0,1,2,3,4,5]  │
                  └────────┬───────┘
                           │
         ┌─────────────────┼─────────────────┬──────────────┐
         │                 │                 │              │
         ▼                 ▼                 ▼              ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐   ┌─────────┐
    │Worker 0 │      │Worker 1 │      │Worker 2 │   │Worker 3 │
    │ Pull 0  │      │ Pull 1  │      │ Pull 2  │   │ Pull 3  │
    └────┬────┘      └────┬────┘      └────┬────┘   └────┬────┘
         │                │                 │              │
         │ (finishes      │ (finishes      │              │
         │  fast)         │  fast)         │              │
         │                │                 │              │
         ▼                ▼                 ▼              ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐   ┌─────────┐
    │ Pull 4  │      │ Pull 5  │      │ (idle)  │   │ (idle)  │
    └─────────┘      └─────────┘      └─────────┘   └─────────┘
         │                │                                     
         └────────────────┴──────────────────────────────┐
                           │                             │
                           ▼                             │
                    ┌─────────────┐                      │
                    │    Merger   │                      │
                    └──────┬──────┘                      │
                           │                             │
                           ▼                             │
                    ┌─────────────┐                      │
                    │Final Output │                      │
                    └─────────────┘                      │
                                                         │
   NOTE: Workers 0 & 1 completed 2 tasks each  ◄────────┘
         Workers 2 & 3 completed 1 task each
         (Better load balancing!)
```

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Jetstream2 Cloud                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Master VM (149.165.170.232)                         │  │
│  │                                                       │  │
│  │  • Ubuntu 22.04, m3.medium                          │  │
│  │  • Python 3.10, FFmpeg 4.4.2                        │  │
│  │  • NFS Server                                       │  │
│  │  • SSH Client (connects to workers)                │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                             │
│               │ SSH Commands                                │
│               │ (port 22)                                   │
│               │                                             │
│  ┌────────────┼──────────────────────┬───────────┬────────┤
│  │            │                      │           │        │
│  │            ▼                      ▼           ▼        │
│  │  ┌─────────────────┐   ┌─────────────────┐           │
│  │  │ Worker 1        │   │ Worker 2        │  ...      │
│  │  │ .199            │   │ .58             │           │
│  │  │                 │   │                 │           │
│  │  │ • NFS Client    │   │ • NFS Client    │           │
│  │  │ • SSH Server    │   │ • SSH Server    │           │
│  │  │ • FFmpeg        │   │ • FFmpeg        │           │
│  │  └─────────────────┘   └─────────────────┘           │
│  │                                                        │
│  │                                                        │
│  │         ┌────────────────────────────┐                │
│  │         │  NFS Mount Point           │                │
│  │         │  /home/ubuntu/nfs_shared   │                │
│  │         │                            │                │
│  │         │  Mounted on ALL 5 VMs      │                │
│  │         │  via NFS protocol          │                │
│  │         │  (port 2049)               │                │
│  │         └────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## Processing Timeline (Dynamic Scheduling)

```
Time →
Master:  [Segment Video] ──────────────────────────────► [Merge] [Done]
         0.5s                                            0.5s

Worker 0: ════════[Chunk 0: 1.28s]════════ ════[Chunk 4: 1.19s]════
Worker 1: ════════[Chunk 1: 1.35s]════════ ════[Chunk 5: 1.28s]════
Worker 2: ════════════[Chunk 2: 1.64s]════════════
Worker 3: ════════════[Chunk 3: 1.61s]════════════

Legend:
  ════  Processing
  ──── Idle/Waiting

Total: 6.03 seconds (measured from start to finish)

Key Observation:
- Workers 0 & 1 finished first, immediately grabbed chunks 4 & 5
- Workers 2 & 3 remained idle after completing their first chunk
- Dynamic scheduling maximized resource utilization
```

---

## File System Layout

```
Master Node:
/home/ubuntu/nfs_shared/          ← NFS Export (shared to all)
  ├── test_input.mp4              ← Original input video (855KB)
  ├── chunks/                     ← Segmented input chunks
  │   ├── chunk_000.mp4          (Created by master)
  │   ├── chunk_001.mp4
  │   ├── chunk_002.mp4
  │   ├── chunk_003.mp4
  │   ├── chunk_004.mp4
  │   └── chunk_005.mp4
  ├── processed/                  ← Worker outputs
  │   ├── chunk_000.mp4          (Written by workers via NFS)
  │   ├── chunk_001.mp4
  │   ├── chunk_002.mp4
  │   ├── chunk_003.mp4
  │   ├── chunk_004.mp4
  │   └── chunk_005.mp4
  └── output/                     ← Final merged video
      ├── final_dynamic.mp4      (4.2MB, 30 seconds)
      └── final_static.mp4       (4.2MB, 30 seconds)

Worker Nodes:
/home/ubuntu/nfs_shared/          ← NFS Mount (same as master)
  (All workers see the same files via NFS)
```

---

## Communication Protocols

### SSH Command Execution

```
┌─────────────┐                              ┌─────────────┐
│   Master    │                              │   Worker    │
│             │                              │             │
│ Python      │  1. SSH Connection           │ SSH Daemon  │
│ subprocess  │─────────────────────────────>│             │
│             │     (port 22, key auth)      │             │
│             │                              │             │
│             │  2. Execute Command          │             │
│             │     "ffmpeg -i input.mp4..." │             │
│             │─────────────────────────────>│ FFmpeg      │
│             │                              │ Process     │
│             │                              │             │
│             │  3. Return stdout/stderr     │             │
│             │<─────────────────────────────│             │
│             │                              │             │
│ Parse       │  4. Connection Close         │             │
│ Results     │<─────────────────────────────│             │
│             │                              │             │
└─────────────┘                              └─────────────┘
```

### NFS File Access

```
┌─────────────┐                              ┌─────────────┐
│   Master    │                              │ NFS Server  │
│             │                              │  (Master)   │
│ Write       │  1. Write Request            │             │
│ Chunk File  │─────────────────────────────>│ Store File  │
│             │     (port 2049, NFS v4)      │             │
└─────────────┘                              └──────┬──────┘
                                                    │
                                                    │ NFS Export
                                                    │
┌─────────────┐                                    │
│   Worker    │                                    │
│             │  2. Read Request                   │
│ Read Chunk  │<───────────────────────────────────┘
│ via NFS     │                                    
│             │  3. Process with FFmpeg            
│ FFmpeg      │                                    
│ Processes   │                                    
│             │  4. Write Output                   
│ Write to    │─────────────────────────────────>  
│ NFS         │     (same shared storage)          
└─────────────┘                                    
```

---

## Configuration Flow

```
┌──────────────────────────────────────────────────────────┐
│  config/config.yaml (Jetstream)                          │
├──────────────────────────────────────────────────────────┤
│  nfs_base_dir: "/home/ubuntu/nfs_shared"                │
│  ssh_user: "exouser"                                     │
│  workers:                                                │
│    - host: "149.165.169.199"                            │
│    - host: "149.165.169.58"                             │
│    - host: "149.165.169.92"                             │
│    - host: "149.165.172.111"                            │
│  segment_duration: 5                                     │
└──────────────────────────────────────────────────────────┘
                      │
                      │ Loaded by main.py
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  Master Coordinator                                      │
│  • Creates 4 RemoteWorker instances                      │
│  • Each with ssh_host from config                       │
│  • NFS paths for chunks, processed, output              │
└──────────────────────────────────────────────────────────┘
                      │
                      │ When --remote flag used
                      │
                      ▼
              Execute on Jetstream2


┌──────────────────────────────────────────────────────────┐
│  config/config.local.yaml (Local Testing)                │
├──────────────────────────────────────────────────────────┤
│  nfs_base_dir: "/tmp/video_processing"                  │
│  workers:                                                │
│    - host: "localhost"                                   │
│    - host: "localhost"                                   │
│    - host: "localhost"                                   │
└──────────────────────────────────────────────────────────┘
                      │
                      │ Loaded by main.py
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  Master Coordinator                                      │
│  • Creates 3 LocalWorker instances                       │
│  • Local paths in /tmp                                   │
└──────────────────────────────────────────────────────────┘
                      │
                      │ When --remote flag NOT used
                      │
                      ▼
              Execute locally
```

---

## Summary

**Key Architectural Decisions:**

1. **Master-Worker Pattern**: Centralized orchestration with distributed execution
2. **NFS Shared Storage**: Zero-copy file access eliminates network transfers
3. **SSH Remote Execution**: Simple, secure, standard Linux tool
4. **ThreadPoolExecutor**: Python's built-in concurrency for I/O-bound SSH operations
5. **Dynamic Scheduling**: Queue-based task assignment for automatic load balancing
6. **Pluggable Workers**: RemoteWorker and LocalWorker share interface for testing

**Performance Characteristics:**
- Local: 0.79s (dynamic), 0.94s (static)
- Cloud: 6.03s (dynamic), 6.08s (static)
- Success Rate: 100% across all tests
- Load Distribution: Workers 0&1 completed 2 chunks, Workers 2&3 completed 1 chunk
