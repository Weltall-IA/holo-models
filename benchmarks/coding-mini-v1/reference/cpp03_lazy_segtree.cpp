#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

static constexpr int64_t MOD = 1000000007LL;

inline int64_t norm(int64_t x) {
    x %= MOD;
    if (x < 0) x += MOD;
    return x;
}

struct Node {
    int64_t sum;
    int64_t mul;
    int64_t add;
    int len;
};

class SegmentTree {
private:
    int n;
    vector<Node> tree;

    void apply_tag(int u, int64_t m, int64_t a) {
        tree[u].sum = (tree[u].sum * m + a * tree[u].len) % MOD;
        tree[u].mul = (tree[u].mul * m) % MOD;
        tree[u].add = (tree[u].add * m + a) % MOD;
    }

    void push(int u) {
        if (tree[u].mul == 1 && tree[u].add == 0) return;
        apply_tag(2 * u, tree[u].mul, tree[u].add);
        apply_tag(2 * u + 1, tree[u].mul, tree[u].add);
        tree[u].mul = 1;
        tree[u].add = 0;
    }

    void pull(int u) {
        tree[u].sum = (tree[2 * u].sum + tree[2 * u + 1].sum) % MOD;
    }

    void build(int u, int l, int r, const vector<int64_t> &init_data) {
        tree[u].mul = 1;
        tree[u].add = 0;
        tree[u].len = r - l + 1;
        if (l == r) {
            tree[u].sum = norm(init_data[l]);
            return;
        }
        int mid = l + (r - l) / 2;
        build(2 * u, l, mid, init_data);
        build(2 * u + 1, mid + 1, r, init_data);
        pull(u);
    }

    void update_affine(int u, int l, int r, int ql, int qr, int64_t m, int64_t a) {
        if (ql <= l && r <= qr) {
            apply_tag(u, m, a);
            return;
        }
        push(u);
        int mid = l + (r - l) / 2;
        if (ql <= mid) {
            update_affine(2 * u, l, mid, ql, qr, m, a);
        }
        if (qr > mid) {
            update_affine(2 * u + 1, mid + 1, r, ql, qr, m, a);
        }
        pull(u);
    }

    int64_t query_sum(int u, int l, int r, int ql, int qr) {
        if (ql <= l && r <= qr) {
            return tree[u].sum;
        }
        push(u);
        int mid = l + (r - l) / 2;
        int64_t res = 0;
        if (ql <= mid) {
            res = (res + query_sum(2 * u, l, mid, ql, qr)) % MOD;
        }
        if (qr > mid) {
            res = (res + query_sum(2 * u + 1, mid + 1, r, ql, qr)) % MOD;
        }
        return res;
    }

public:
    SegmentTree(const vector<int64_t> &init_data) {
        n = static_cast<int>(init_data.size());
        tree.resize(4 * n + 1);
        build(1, 0, n - 1, init_data);
    }

    void add_range(int l, int r, int64_t val) {
        update_affine(1, 0, n - 1, l, r, 1, norm(val));
    }

    void mul_range(int l, int r, int64_t val) {
        update_affine(1, 0, n - 1, l, r, norm(val), 0);
    }

    int64_t query(int l, int r) {
        return query_sum(1, 0, n - 1, l, r);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, q;
    if (!(cin >> n >> q)) return 0;

    vector<int64_t> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    SegmentTree st(a);

    string op;
    for (int i = 0; i < q; ++i) {
        if (!(cin >> op)) break;
        if (op == "ADD") {
            int l, r;
            int64_t x;
            cin >> l >> r >> x;
            st.add_range(l, r, x);
        } else if (op == "MUL") {
            int l, r;
            int64_t x;
            cin >> l >> r >> x;
            st.mul_range(l, r, x);
        } else if (op == "SUM") {
            int l, r;
            cin >> l >> r;
            cout << st.query(l, r) << "\n";
        }
    }

    return 0;
}
