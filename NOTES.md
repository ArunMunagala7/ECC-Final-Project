# Development Notes

Quick notes from building this project.

## Setup Challenges

### NFS Permissions
Had permission errors when writing to NFS. Fixed with:
```bash
sudo chown -R exouser:exouser /home/ubuntu/nfs_shared
```

### SSH Authentication
Workers kept asking for passwords. Set up SSH keys:
```bash
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
# Then copied public key to each worker's authorized_keys
```

### Segmentation Bug
Initially had corrupted last chunk (262 bytes). Fixed calculation:
- Before: `num_segments = ceil(duration / segment_duration) + 1`
- After: `num_segments = ceil(duration / segment_duration)`

Fixed in commit 8aeb026.

## Test Results

### Local (Mac)
- Dynamic: 0.79s (100% success)
- Static: 0.94s (100% success)
- Dynamic is 16% faster

### Cloud (Jetstream2 - 4 workers)
- Dynamic: 6.03s (100% success, 6 segments)
- Static: 6.08s (100% success, 6 segments)
- Load distribution: Workers 0&1 did 2 chunks each, Workers 2&3 did 1 each

## Demo Checklist

- [ ] Test local demo once before presenting
- [ ] SSH to master VM to verify connectivity
- [ ] Have screenshots as backup
- [ ] Mention 100% success rate
- [ ] Explain why cloud is slower (network overhead)
- [ ] Emphasize dynamic scheduling advantage

## Useful Commands

```bash
# Test local
cd hybrid-nfs-implementation
python3 src/main.py --input test_videos/test_input.mp4 --strategy dynamic --config config/config.local.yaml

# Test cloud
ssh exouser@149.165.170.232
cd ~/video_processing
python3 src/main.py --input /home/ubuntu/nfs_shared/test_input.mp4 --strategy dynamic --config config/config.yaml --remote
```
