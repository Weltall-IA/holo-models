#include <cstdint>
#include <deque>
#include <iostream>
#include <vector>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    vector<int64_t> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    if (k <= 0 || k > n) {
        cout << "INVALID\n";
        return 0;
    }

    deque<int> min_dq;
    deque<int> max_dq;
    int64_t current_sum = 0;

    for (int i = 0; i < n; ++i) {
        current_sum += a[i];

        // Maintain monotonic min deque
        while (!min_dq.empty() && a[min_dq.back()] >= a[i]) {
            min_dq.pop_back();
        }
        min_dq.push_back(i);

        // Maintain monotonic max deque
        while (!max_dq.empty() && a[max_dq.back()] <= a[i]) {
            max_dq.pop_back();
        }
        max_dq.push_back(i);

        // Remove elements outside current window
        while (!min_dq.empty() && min_dq.front() <= i - k) {
            min_dq.pop_front();
        }
        while (!max_dq.empty() && max_dq.front() <= i - k) {
            max_dq.pop_front();
        }

        // When window is fully formed
        if (i >= k - 1) {
            cout << current_sum << " " << a[min_dq.front()] << " " << a[max_dq.front()] << "\n";
            current_sum -= a[i - k + 1];
        }
    }

    return 0;
}
