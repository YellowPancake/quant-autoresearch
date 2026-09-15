# Framework tests

Run from the distribution repository when maintaining the framework:

```sh
python3 -m unittest -v
```

Tests use temporary workspaces. Synthetic prices are internal software-test fixtures;
the user-facing examples use the bundled CSI300 and S&P 500 histories. These tests
check framework behavior, not real-market strategy performance.

维护框架时可在仓库根目录运行上述命令。普通用户启动研究无需执行此步骤。
