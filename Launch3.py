import shardedBot

if __name__ == "__main__":
    instance = 2
    instances = 4
    shards = 84
    shard_ids = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62]
    shardedBot.NekoBot(instance=instance, instances=instances, shard_count=shards, shard_ids=shard_ids, max_messages=101).run()
