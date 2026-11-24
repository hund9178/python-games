import random

def play():
    print("\n" + "=" * 30)
    print("   🎯 猜数字游戏")
    print("=" * 30)
    print("我想了一个 1 到 100 之间的数字，你来猜猜看！")

    number = random.randint(1, 100)
    count = 0
    max_guess = 10  # 最多猜 10 次

    while count < max_guess:
        try:
            guess = int(input(f"\n第 {count + 1} 次，请输入你的猜测："))
        except ValueError:
            print("❌ 请输入一个整数！")
            continue

        count += 1

        if guess == number:
            print(f"\n🎉 恭喜你！猜对了！就是 {number}，你用了 {count} 次！")
            if count <= 3:
                print("🏆 太强了，你是天才！")
            elif count <= 6:
                print("👍 不错不错，很厉害！")
            else:
                print("😄 还好最后猜到了！")
            break
        elif guess > number:
            print("📉 太大了！")
        else:
            print("📈 太小了！")

        remaining = max_guess - count
        if remaining > 0:
            print(f"   还剩 {remaining} 次机会")

    else:
        print(f"\n😢 机会用完了！正确答案是 {number}")

    again = input("\n再玩一次？(y/n)：").strip().lower()
    if again == "y":
        play()
    else:
        print("👋 下次再见！")

if __name__ == "__main__":
    play()
