# Elastic Distributed Video Processing - Quick Reference Slides

## Slide 1: Title
**Elastic Distributed Video Processing Framework**  
**with Dynamic Workload Partitioning**

Team: Anuj Prakash, Arun Munagala, Shreyas Amit Dhekane  
Indiana University Bloomington  
Elastic Cloud Computing

---

## Slide 2: Problem
**Challenge:** Traditional single-machine video processing can't scale

- Streaming platforms need to process thousands of videos
- Single machine = bottleneck
- Can't leverage cloud resources
- Processing time scales linearly

**Solution:** Distributed processing with smart workload partitioning

---

## Slide 3: Architecture
```
MASTER NODE
  ↓ Segments video
  ↓ Creates task queue
  ↓ Coordinates workers
  ↓
WORKERS (2, 4, 8...)
  ↓ Process chunks with FFmpeg
  ↓ Report completion
  ↓
MERGE RESULTS
  ↓
FINAL OUTPUT
```

---

## Slide 4: Three Strategies

**1. Single Machine (Baseline)**
- One machine processes everything
- Time: 1.65s
- No parallelism

**2. Static Partitioning**
- Fixed assignment to workers
- Time: 1.00s (1.6x faster)
- Problem: Load imbalance

**3. Dynamic Scheduling** ⭐
- Workers fetch from queue
- Time: 0.90s (1.8x faster)
- Better load balancing

---

## Slide 5: Key Results

### Local Testing (Thread-Based):
| Workers | Speedup | Efficiency |
|---------|---------|------------|
| 1 | 1.0x | 100% |
| 2 | 1.8x | 91% ✅ |
| 4 | 3.0x | 75% |
| 8 | 4.5x | 56% |

### Cloud Testing (SSH/SCP):
- Dynamic **50% faster** than static
- Network overhead visible for small videos
- Benefits increase with video size

---

## Slide 6: Two Implementations

**Thread-Based (Main)**
- 2,428 lines of code
- Comprehensive metrics & visualization
- Works locally
- Best for development

**SSH/SCP-Based**
- 528 lines of code
- Real cloud deployment
- Actual network testing
- Best for production

---

## Slide 7: Key Findings

1. ✅ **Dynamic beats static** (10-20% faster)
2. ✅ **Network overhead matters** (distribution not always faster)
3. ✅ **Optimal chunk size:** 10-15 seconds
4. ✅ **Load balancing critical** (reduces idle time)
5. ✅ **Scalable up to 4 workers** (then diminishing returns)

---

## Slide 8: Challenges Solved

- ✅ Segment ordering and merging
- ✅ FFmpeg compatibility
- ✅ Thread safety (shared queue)
- ✅ SSH/SCP overhead mitigation
- ✅ Python import issues

---

## Slide 9: Demo

**Live Demo Commands:**
```bash
# Quick demo
./scripts/demo.sh

# Benchmark
python3 src/evaluation/benchmark.py --input demo/sample.mp4 --workers 1,2,4,8

# Custom video
python3 src/main.py --input video.mp4 --output result.mp4 --workers 4 --strategy dynamic
```

---

## Slide 10: Conclusion

**Contributions:**
- ✅ Complete distributed video processing framework
- ✅ Validated dynamic scheduling superiority
- ✅ Two implementations (local + cloud)
- ✅ Production-ready, cloud-deployable

**Impact:**
- Applicable to streaming platforms
- Scalable to enterprise workloads
- Open source for research

**Questions?**

---

## Backup Slides

### Detailed Performance Data
- See PRESENTATION.md Appendix A

### Code Architecture
- Master: src/master/__init__.py
- Worker: src/worker/__init__.py
- Queue: src/core/task_queue.py

### Setup Instructions
- See GETTING_STARTED.md

### GitHub
- https://github.com/ArunMunagala7/ECC-Final-Project
