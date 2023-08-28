import json

import pandas as pd
import operator


class SecureDataFrame:
    def __init__(self, df, df_name, data_rules, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.df = df
        self.data_rules = data_rules
        self.df_name = df_name  # Nome do DataFrame
        self.security_column = 'security_group'

    def create_security_column(self):
        self.df[self.security_column] = ''

        allowed_dfs = self.data_rules.get("allowed_dfs", [])
        groups = self.data_rules.get("groups", {})

        if self.df_name in allowed_dfs:
            self.df[self.security_column] = 'all'
            return
        for group, group_data in groups.items():
            for df_name, df_rules in group_data.items():
                if df_name == self.df_name:
                    self._apply_df_rules(df_rules, group)

    def _apply_df_rules(self, df_rules, group):
        column_rules = df_rules.get("column_rules", {})
        filter_rules = df_rules.get("filter_rules")
        enable_all = df_rules.get("enable_all", False)

        if enable_all:
            self.df.loc[self.security_column] = self.df.loc[self.security_column].apply(lambda x: x + f';{group}')
        else:
            if filter_rules:
                self._apply_filter_rules(filter_rules, group)
            elif column_rules:
                if column_rules.get("and"):
                    self._apply_and_column_rules(column_rules["and"], group)

                if column_rules.get("or"):
                    self._apply_or_column_rules(column_rules["or"], group)

    def _apply_filter_rules(self, filter_rules, group):
        indexes = self.df.query(filter_rules).index
        self.df.loc[indexes, self.security_column] = self.df.loc[indexes, self.security_column].apply(lambda x: x + f';{group}')

    def _apply_and_column_rules(self, rules, group):
        result = pd.Series(True, index=self.df.index)
        for col, operation_text in rules.items():
            operation_func = self._parse_operation(operation_text)
            result &= operation_func(self.df[col])
        indexes = result[result].index
        self.df.loc[indexes, self.security_column] = self.df.loc[indexes, self.security_column].apply(lambda x: x + f';{group}')

    def _apply_or_column_rules(self, rules, group):
        result = pd.Series(False, index=self.df.index)
        for col, operation_text in rules.items():
            operation_func = self._parse_operation(operation_text)
            result |= operation_func(self.df[col])
        indexes = result[result].index
        self.df.loc[indexes, self.security_column] = self.df.loc[indexes, self.security_column].apply(lambda x: x + f';{group}')

    def _parse_operation(self, operation_text):
        operators = {
            ">": operator.gt,
            ">=": operator.ge,
            "<": operator.lt,
            "<=": operator.le,
            "!=": operator.ne,
            "==": operator.eq,
            "=:=": self._contains
        }
        for op, operation_name in operators.items():
            if op in operation_text:
                col_name, op = operation_text.split(op)
                op = op.strip()
                return lambda col: operation_name(col, op)
        raise ValueError(f"Invalid operation: {operation_text}")

    @staticmethod
    def _contains(col, value):
        return col.str.contains(value)




def read_data_rules(filename):
    with open(f'{filename}') as f:
        return json.loads(f.read())

if __name__ == "__main__":
    df = pd.DataFrame.from_records([{"a": 1}, {"a": 3}, {"a": 5}, {"a": 7}])
    df_name = SecureDataFrame(df, "df_name", read_data_rules("rls_rules.json"))
    df = pd.DataFrame.from_records([{"a": 8}, {"a": 93}, {"a": 45}, {"a": 75}])
    df_name_2 = SecureDataFrame("df_name_2", read_data_rules("rls_rules.json"))
    # df_name_3 = pd.DataFrame("df_name_3", read_data_rules("rls_rules.json"), data=[{"a": 1}, {"a": 3}, {"a": 5}, {"a": 7}])
