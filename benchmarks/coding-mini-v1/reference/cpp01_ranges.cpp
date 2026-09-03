#include <algorithm>
#include <cstdint>
#include <iostream>
#include <vector>

using namespace std;

struct Range {
    int64_t l;
    int64_t r;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<Range> ranges(n);
    for (int i = 0; i < n; ++i) {
        if (!(cin >> ranges[i].l >> ranges[i].r)) return 0;
        if (ranges[i].l > ranges[i].r) {
            cout << "INVALID\n";
            return 0;
        }
    }

    if (n == 0) {
        cout << 0 << "\n";
        return 0;
    }

    sort(ranges.begin(), ranges.end(), [](const Range &a, const Range &b) {
        if (a.l != b.l) return a.l < b.l;
        return a.r < b.r;
    });

    vector<Range> merged;
    merged.reserve(n);

    Range current = ranges[0];
    for (int i = 1; i < n; ++i) {
        const Range &next = ranges[i];
        // Check if next overlaps with current (next.l <= current.r)
        // or next is adjacent to current (current.r < INT64_MAX && next.l == current.r + 1)
        bool can_merge = (next.l <= current.r) ||
                         (current.r != INT64_MAX && next.l == current.r + 1);

        if (can_merge) {
            if (next.r > current.r) {
                current.r = next.r;
            }
        } else {
            merged.push_back(current);
            current = next;
        }
    }
    merged.push_back(current);

    cout << merged.size() << "\n";
    for (const auto &rg : merged) {
        cout << rg.l << " " << rg.r << "\n";
    }

    return 0;
}
